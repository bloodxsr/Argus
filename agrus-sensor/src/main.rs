use reqwest::Client;
use serde::Serialize;
use std::time::Duration;
use tokio::time;
use tracing::{info, warn};

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
    info!("Starting AGRUS Rust Sensor (eBPF user-space daemon)...");

    let client = Client::new();
    let host_name = hostname::get()?.into_string().unwrap_or_else(|_| "unknown".to_string());
    
    // In a production Aya-eBPF project, we would load the compiled BPF bytecode into the Linux kernel here:
    // let mut bpf = Bpf::load(include_bytes_aligned!("../../target/bpfel-unknown-none/release/agrus-ebpf"))?;
    // BpfLogger::init(&mut bpf)?;
    info!("eBPF probes attached to sys_enter_execve (process execution)");

    // Simulate an infinite loop listening for kernel events via a RingBuffer
    let mut interval = time::interval(Duration::from_secs(10));
    
    loop {
        interval.tick().await;

        // SIMULATED eBPF KERNEL TRACE: In reality, this data is pulled directly from a Linux Kernel ring buffer
        info!("Kernel Event Detected: Nginx spawned a reverse shell.");
        
        let event = TelemetryEvent {
            schema_version: "1.0".to_string(),
            event_id: format!("evt-{}", uuid::Uuid::new_v4()),
            source: "agrus-rust-sensor".to_string(),
            event_type: "process_spawn".to_string(),
            timestamp: chrono::Utc::now().to_rfc3339(),
            host: host_name.clone(),
            host_ip: "10.0.1.20".to_string(),
            environment: "production".to_string(), // Crucial for our Blast Radius logic
            pid: 4412,
            uid: 33, // www-data
            payload: serde_json::json!({
                "parent": "nginx", 
                "process": "bash", 
                "path": "/tmp/.x/bash",
                "syscall": "sys_enter_execve"
            }),
        };

        // Send the telemetry to the Go Gateway (or Python AI directly for now)
        warn!("Transmitting telemetry to AGRUS backend...");
        let response = client
            .post("http://127.0.0.1:8000/scenarios/rce_c2_beacon/run") // Hitting our Python endpoint for now
            .json(&event)
            .send()
            .await;

        match response {
            Ok(res) => {
                if res.status().is_success() {
                    info!("Telemetry successfully ingested by AI Engine");
                } else {
                    warn!("Backend returned error status: {}", res.status());
                }
            }
            Err(e) => warn!("Failed to connect to backend: {}", e),
        }
    }
}
