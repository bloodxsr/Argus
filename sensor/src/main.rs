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
    tracing_subscriber::fmt::init();
    info!("Starting Real AGRUS Rust Sensor (eBPF user-space daemon)...");

    let client = Client::new();
    let host_name = hostname::get()?.into_string().unwrap_or_else(|_| "unknown-linux".to_string());
    
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
    
    info!("eBPF probes natively attached to sys_enter_execve. Waiting for REAL kernel events...");
    
    // Initialize the real PerfEventArray logger stream from the Kernel
    let mut perf_array = AsyncPerfEventArray::try_from(bpf.take_map("EVENTS").expect("Failed to find EVENTS map")).unwrap();
    let cpus = online_cpus().expect("Failed to get online CPUs");

    let (tx, mut rx) = tokio::sync::mpsc::channel::<TelemetryEvent>(10000);
    let client_clone = client.clone();
    
    // Background worker for network batching
    tokio::spawn(async move {
        let mut batch = Vec::with_capacity(50);
        let mut interval = tokio::time::interval(std::time::Duration::from_millis(500));
        
        loop {
            tokio::select! {
                Some(event) = rx.recv() => {
                    batch.push(event);
                    if batch.len() >= 50 {
                        let expected_token = std::env::var("AGRUS_SENSOR_TOKEN").unwrap_or_else(|_| "default-secure-token".to_string());
                        let _ = client_clone.post("http://127.0.0.1:8080/api/v1/telemetry")
                            .header("Authorization", format!("Bearer {}", expected_token))
                            .json(&batch)
                            .send()
                            .await;
                        batch.clear();
                    }
                }
                _ = interval.tick() => {
                    if !batch.is_empty() {
                        let expected_token = std::env::var("AGRUS_SENSOR_TOKEN").unwrap_or_else(|_| "default-secure-token".to_string());
                        let _ = client_clone.post("http://127.0.0.1:8080/api/v1/telemetry")
                            .header("Authorization", format!("Bearer {}", expected_token))
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
        let host_name_clone = host_name.clone();
        let tx_clone = tx.clone();

        tokio::spawn(async move {
            let mut buffers = (0..10).map(|_| BytesMut::with_capacity(1024)).collect::<Vec<_>>();
            
            loop {
                let events = buf.read_events(&mut buffers).await.unwrap();
                for i in 0..events.read {
                    let ptr = buffers[i].as_ptr() as *const ProcessExecEvent;
                    let data = unsafe { ptr.read_unaligned() };

                    // Parse the C-string from comm
                    let comm_len = data.comm.iter().position(|&c| c == 0).unwrap_or(data.comm.len());
                    let comm_str = String::from_utf8_lossy(&data.comm[..comm_len]).into_owned();

                    info!("Intercepted Process natively from Kernel: {} (PID: {})", comm_str, data.pid);

                    let telemetry = TelemetryEvent {
                        schema_version: "1.0".to_string(),
                        event_id: format!("evt-{}", uuid::Uuid::new_v4()),
                        source: "ebpf".to_string(),
                        event_type: "PROCESS_START".to_string(),
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        host: host_name_clone.clone(),
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

                    let _ = tx_clone.send(telemetry).await;
                    
                    // CRITICAL FIX: Clear the BytesMut cursor so it doesn't exhaust capacity
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
