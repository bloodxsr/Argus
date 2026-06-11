use reqwest::Client;
use serde::Serialize;
use tracing::{info, error};
use aya::Bpf;
use aya::programs::TracePoint;
use aya::maps::perf::AsyncPerfEventArray;
use aya::util::online_cpus;
use bytes::BytesMut;
use tokio::signal;

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct ProcessExecEvent {
    pub pid: u32,
    pub tgid: u32,
    pub comm: [u8; 16],
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct FileAccessEvent {
    pub pid: u32,
    pub tgid: u32,
    pub comm: [u8; 16],
    pub filename: [u8; 256],
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct NetworkConnEvent {
    pub pid: u32,
    pub tgid: u32,
    pub comm: [u8; 16],
    pub dst_addr: u32,
    pub dst_port: u16,
}

// The payload that matches our Python AI Engine's expected format
#[derive(Serialize, Debug, Clone)]
struct TelemetryEvent {
    schema_version: String,
    event_id: String,
    source: String,
    event_type: String,
    timestamp: String,
    host: String,
    host_ip: String,
    environment: String,
    pid: u32,
    uid: u32,
    payload: serde_json::Value,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Attempt to load .env file; ignore if not found
    let _ = dotenvy::dotenv();

    tracing_subscriber::fmt::init();
    info!("Starting Real AGRUS Rust Sensor (eBPF user-space daemon)...");

    let client = Client::new();
    let host_name = hostname::get()?.into_string().unwrap_or_else(|_| "unknown-linux".to_string());
    
    let gateway_url = std::env::var("AGRUS_GATEWAY_URL").unwrap_or_else(|_| {
        error!("CRITICAL: AGRUS_GATEWAY_URL environment variable is required.");
        std::process::exit(1);
    });

    let expected_token = std::env::var("AGRUS_SENSOR_TOKEN").unwrap_or_else(|_| {
        error!("CRITICAL: AGRUS_SENSOR_TOKEN environment variable is required.");
        std::process::exit(1);
    });

    // Attempt to load real eBPF bytecode 
    let bpf_path = "../ebpf/target/bpfel-unknown-none/release/ebpf";
    let bpf_data = match std::fs::read(bpf_path) {
        Ok(data) => data,
        Err(_) => {
            error!("CRITICAL: eBPF bytecode not found at {}. Real sensors require compiled kernel bytecode. Exiting.", bpf_path);
            std::process::exit(1);
        }
    };

    info!("Found eBPF bytecode, loading into kernel...");
    
    let mut bpf = Bpf::load(&bpf_data).expect("Failed to load eBPF bytecode into kernel");
    
    let program: &mut TracePoint = bpf.program_mut("sys_enter_execve").expect("program not found").try_into().expect("not a tracepoint");
    program.load().expect("failed to load program");
    program.attach("syscalls", "sys_enter_execve").expect("failed to attach tracepoint");
    
    let program_open: &mut TracePoint = bpf.program_mut("sys_enter_openat").expect("program not found").try_into().expect("not a tracepoint");
    program_open.load().expect("failed to load program_open");
    program_open.attach("syscalls", "sys_enter_openat").expect("failed to attach openat tracepoint");

    let program_conn: &mut TracePoint = bpf.program_mut("sys_enter_connect").expect("program not found").try_into().expect("not a tracepoint");
    program_conn.load().expect("failed to load program_conn");
    program_conn.attach("syscalls", "sys_enter_connect").expect("failed to attach connect tracepoint");

    info!("eBPF probes natively attached to execve, openat, connect. Waiting for REAL kernel events...");
    
    // Initialize the real PerfEventArray logger streams from the Kernel
    let mut perf_array = AsyncPerfEventArray::try_from(bpf.take_map("EVENTS").expect("Failed to find EVENTS map")).unwrap();
    let mut perf_array_files = AsyncPerfEventArray::try_from(bpf.take_map("FILE_EVENTS").expect("Failed to find FILE_EVENTS map")).unwrap();
    let mut perf_array_net = AsyncPerfEventArray::try_from(bpf.take_map("NET_EVENTS").expect("Failed to find NET_EVENTS map")).unwrap();
    let cpus = online_cpus().expect("Failed to get online CPUs");

    let (tx, mut rx) = tokio::sync::mpsc::channel::<TelemetryEvent>(10000);
    let client_clone = client.clone();
    
    let gateway_url_clone = gateway_url.clone();
    let token_clone = expected_token.clone();

    // Background worker for network batching
    tokio::spawn(async move {
        let mut batch = Vec::with_capacity(50);
        let mut interval = tokio::time::interval(std::time::Duration::from_millis(500));
        
        loop {
            tokio::select! {
                Some(event) = rx.recv() => {
                    batch.push(event);
                    if batch.len() >= 50 {
                        let _ = client_clone.post(&gateway_url_clone)
                            .header("Authorization", format!("Bearer {}", token_clone))
                            .json(&batch)
                            .send()
                            .await;
                        batch.clear();
                    }
                }
                _ = interval.tick() => {
                    if !batch.is_empty() {
                        let _ = client_clone.post(&gateway_url_clone)
                            .header("Authorization", format!("Bearer {}", token_clone))
                            .json(&batch)
                            .send()
                            .await;
                        batch.clear();
                    }
                }
            }
        }
    });

    for cpu in cpus {
        let mut buf = perf_array.open(cpu, None).unwrap();
        let mut buf_files = perf_array_files.open(cpu, None).unwrap();
        let mut buf_net = perf_array_net.open(cpu, None).unwrap();
        
        let host_name_clone1 = host_name.clone();
        let tx_clone1 = tx.clone();
        tokio::spawn(async move {
            let mut buffers = (0..10).map(|_| BytesMut::with_capacity(1024)).collect::<Vec<_>>();
            loop {
                let events = buf.read_events(&mut buffers).await.unwrap();
                for i in 0..events.read {
                    let ptr = buffers[i].as_ptr() as *const ProcessExecEvent;
                    let data = unsafe { ptr.read_unaligned() };
                    let comm_len = data.comm.iter().position(|&c| c == 0).unwrap_or(data.comm.len());
                    let comm_str = String::from_utf8_lossy(&data.comm[..comm_len]).into_owned();

                    let telemetry = TelemetryEvent {
                        schema_version: "1.0".to_string(),
                        event_id: format!("evt-{}", uuid::Uuid::new_v4()),
                        source: "ebpf".to_string(),
                        event_type: "PROCESS_START".to_string(),
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        host: host_name_clone1.clone(),
                        host_ip: "10.0.1.20".to_string(),
                        environment: "production".to_string(), 
                        pid: data.pid,
                        uid: 0, 
                        payload: serde_json::json!({
                            "process": comm_str,
                            "process_id": data.pid, 
                            "thread_group_id": data.tgid,
                            "live": true,
                            "type": "sys_enter_execve"
                        }),
                    };
                    let _ = tx_clone1.send(telemetry).await;
                    buffers[i].clear();
                }
            }
        });

        let host_name_clone2 = host_name.clone();
        let tx_clone2 = tx.clone();
        tokio::spawn(async move {
            let mut buffers = (0..10).map(|_| BytesMut::with_capacity(1024)).collect::<Vec<_>>();
            loop {
                let events = buf_files.read_events(&mut buffers).await.unwrap();
                for i in 0..events.read {
                    let ptr = buffers[i].as_ptr() as *const FileAccessEvent;
                    let data = unsafe { ptr.read_unaligned() };
                    let comm_len = data.comm.iter().position(|&c| c == 0).unwrap_or(data.comm.len());
                    let comm_str = String::from_utf8_lossy(&data.comm[..comm_len]).into_owned();
                    let filename_len = data.filename.iter().position(|&c| c == 0).unwrap_or(data.filename.len());
                    let filename_str = String::from_utf8_lossy(&data.filename[..filename_len]).into_owned();

                    let telemetry = TelemetryEvent {
                        schema_version: "1.0".to_string(),
                        event_id: format!("evt-{}", uuid::Uuid::new_v4()),
                        source: "ebpf".to_string(),
                        event_type: "FILE_ACCESS".to_string(),
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        host: host_name_clone2.clone(),
                        host_ip: "10.0.1.20".to_string(),
                        environment: "production".to_string(), 
                        pid: data.pid,
                        uid: 0, 
                        payload: serde_json::json!({
                            "process": comm_str,
                            "process_id": data.pid, 
                            "thread_group_id": data.tgid,
                            "filename": filename_str,
                            "live": true,
                            "type": "sys_enter_openat"
                        }),
                    };
                    let _ = tx_clone2.send(telemetry).await;
                    buffers[i].clear();
                }
            }
        });

        let host_name_clone3 = host_name.clone();
        let tx_clone3 = tx.clone();
        tokio::spawn(async move {
            let mut buffers = (0..10).map(|_| BytesMut::with_capacity(1024)).collect::<Vec<_>>();
            loop {
                let events = buf_net.read_events(&mut buffers).await.unwrap();
                for i in 0..events.read {
                    let ptr = buffers[i].as_ptr() as *const NetworkConnEvent;
                    let data = unsafe { ptr.read_unaligned() };
                    let comm_len = data.comm.iter().position(|&c| c == 0).unwrap_or(data.comm.len());
                    let comm_str = String::from_utf8_lossy(&data.comm[..comm_len]).into_owned();
                    let ip = std::net::Ipv4Addr::from(u32::from_be(data.dst_addr));

                    let telemetry = TelemetryEvent {
                        schema_version: "1.0".to_string(),
                        event_id: format!("evt-{}", uuid::Uuid::new_v4()),
                        source: "ebpf".to_string(),
                        event_type: "NETWORK_CONNECT".to_string(),
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        host: host_name_clone3.clone(),
                        host_ip: "10.0.1.20".to_string(),
                        environment: "production".to_string(), 
                        pid: data.pid,
                        uid: 0, 
                        payload: serde_json::json!({
                            "process": comm_str,
                            "process_id": data.pid, 
                            "thread_group_id": data.tgid,
                            "dst_ip": ip.to_string(),
                            "dst_port": data.dst_port,
                            "live": true,
                            "type": "sys_enter_connect"
                        }),
                    };
                    let _ = tx_clone3.send(telemetry).await;
                    buffers[i].clear();
                }
            }
        });
    }
    
    info!("Kernel Event stream is live. To transmit to the gateway, ensure the NATS routing is active.");
    
    // Wait for Ctrl+C
    info!("Waiting for Ctrl-C...");
    signal::ctrl_c().await?;
    info!("Exiting...");

    Ok(())
}
