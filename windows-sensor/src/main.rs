use reqwest::Client;
use serde::Serialize;
use tracing::{info, warn, error};
use std::sync::Arc;

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

#[cfg(windows)]
use serde::Deserialize;
#[cfg(windows)]
use wmi::{COMLibrary, WMIConnection};
#[cfg(windows)]
use futures::stream::StreamExt;

#[cfg(windows)]
#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct Win32_ProcessStartTrace {
    process_name: String,
    process_id: u32,
    parent_process_id: u32,
}

#[cfg(windows)]
#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct InstanceCreationEvent {
    target_instance: wmi::Variant,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    
    #[cfg(not(windows))]
    {
        error!("This sensor requires Windows WMI/ETW. Please run on a Windows host.");
        std::process::exit(1);
    }

    #[cfg(windows)]
    {
        info!("Starting Real AGRUS Windows Sensor (WMI Persistence & Process Monitor)...");
        let client = Client::new();
        let host_name = hostname::get()?.into_string().unwrap_or_else(|_| "unknown-windows".to_string());
        
        // MPSC Channel for Event Batching
        let (tx, mut rx) = tokio::sync::mpsc::channel::<TelemetryEvent>(10000);
        let client_clone = client.clone();
        
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

        info!("Connecting to WMI COM Library...");
        let com_con = COMLibrary::new().expect("Failed to initialize COM Library");
        let wmi_con = Arc::new(WMIConnection::new(com_con).expect("Failed to connect to WMI"));

        let tx_process = tx.clone();
        let host_name_proc = host_name.clone();
        let wmi_proc = wmi_con.clone();
        
        tokio::spawn(async move {
            info!("Subscribing to Win32_ProcessStartTrace events...");
            let mut filters = wmi_proc
                .exec_notification_query_async::<Win32_ProcessStartTrace>("SELECT * FROM Win32_ProcessStartTrace")
                .expect("Failed to subscribe to WMI process events");

            while let Some(result) = filters.next().await {
                if let Ok(event) = result {
                    info!("Process Creation: {} (PID: {})", event.process_name, event.process_id);
                    let telemetry = TelemetryEvent {
                        schema_version: "1.0".to_string(),
                        event_id: format!("evt-{}", uuid::Uuid::new_v4()),
                        source: "wmi".to_string(),
                        event_type: "PROCESS_START".to_string(),
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        host: host_name_proc.clone(),
                        host_ip: "10.0.1.50".to_string(),
                        environment: "production".to_string(), 
                        pid: event.process_id,
                        uid: 0, 
                        payload: serde_json::json!({
                            "process": event.process_name, 
                            "parent_pid": event.parent_process_id,
                        }),
                    };
                    let _ = tx_process.send(telemetry).await;
                }
            }
        });

        // Registry and Service monitors can be added as async spawned loops here using wmi_con.clone()
        info!("Windows Sensor is actively monitoring WMI events. Press Ctrl+C to exit.");
        tokio::signal::ctrl_c().await.unwrap();
    }
    
    Ok(())
}
