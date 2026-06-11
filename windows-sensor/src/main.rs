#![allow(unused_imports, dead_code, unreachable_code)]
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

#[cfg(windows)]
#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct Win32Service {
    name: String,
    path_name: Option<String>,
    start_mode: Option<String>,
}

#[cfg(windows)]
#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct ServiceCreationEvent {
    target_instance: Win32Service,
}

#[cfg(windows)]
#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct RegistryValueChangeEvent {
    hive: String,
    key_path: String,
    value_name: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    let _ = dotenvy::dotenv();
    
    #[cfg(not(windows))]
    {
        error!("This sensor requires Windows WMI/ETW. Please run on a Windows host.");
        std::process::exit(1);
    }

    #[cfg(windows)]
    {
        info!("Starting Real AGRUS Windows Sensor (WMI Persistence & Process Monitor)...");
        
        let sensor_token = match std::env::var("AGRUS_SENSOR_TOKEN") {
            Ok(val) => val,
            Err(_) => {
                error!("CRITICAL: AGRUS_SENSOR_TOKEN environment variable not set. Exiting.");
                std::process::exit(1);
            }
        };
        let gateway_url = std::env::var("AGRUS_GATEWAY_URL").unwrap_or_else(|_| "http://127.0.0.1:8080/api/v1/telemetry".to_string());

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
                            let _ = client_clone.post(&gateway_url)
                                .header("Authorization", format!("Bearer {}", sensor_token))
                                .json(&batch)
                                .send()
                                .await;
                            batch.clear();
                        }
                    }
                    _ = interval.tick() => {
                        if !batch.is_empty() {
                            let _ = client_clone.post(&gateway_url)
                                .header("Authorization", format!("Bearer {}", sensor_token))
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

        let tx_service = tx.clone();
        let host_name_service = host_name.clone();
        let wmi_service = wmi_con.clone();
        
        tokio::spawn(async move {
            info!("Subscribing to Win32_Service creation events...");
            let mut filters = wmi_service
                .exec_notification_query_async::<ServiceCreationEvent>("SELECT * FROM __InstanceCreationEvent WITHIN 5 WHERE TargetInstance ISA 'Win32_Service'")
                .expect("Failed to subscribe to WMI service events");

            while let Some(result) = filters.next().await {
                if let Ok(event) = result {
                    let service = event.target_instance;
                    info!("Service Installed: {}", service.name);
                    let telemetry = TelemetryEvent {
                        schema_version: "1.0".to_string(),
                        event_id: format!("evt-{}", uuid::Uuid::new_v4()),
                        source: "wmi".to_string(),
                        event_type: "SERVICE_INSTALL".to_string(),
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        host: host_name_service.clone(),
                        host_ip: "10.0.1.50".to_string(),
                        environment: "production".to_string(), 
                        pid: 0,
                        uid: 0, 
                        payload: serde_json::json!({
                            "service_name": service.name,
                            "path": service.path_name.unwrap_or_default(),
                            "start_mode": service.start_mode.unwrap_or_default(),
                        }),
                    };
                    let _ = tx_service.send(telemetry).await;
                }
            }
        });

        let tx_registry = tx.clone();
        let host_name_registry = host_name.clone();
        let wmi_registry = wmi_con.clone();
        
        tokio::spawn(async move {
            info!("Subscribing to Registry Run key modification events...");
            let query = "SELECT * FROM RegistryValueChangeEvent WHERE Hive='HKEY_LOCAL_MACHINE' AND KeyPath='SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run'";
            let mut filters = wmi_registry
                .exec_notification_query_async::<RegistryValueChangeEvent>(query)
                .expect("Failed to subscribe to WMI registry events");

            while let Some(result) = filters.next().await {
                if let Ok(event) = result {
                    info!("Registry Modified: {}\\{}\\{}", event.hive, event.key_path, event.value_name);
                    let telemetry = TelemetryEvent {
                        schema_version: "1.0".to_string(),
                        event_id: format!("evt-{}", uuid::Uuid::new_v4()),
                        source: "wmi".to_string(),
                        event_type: "REGISTRY_MODIFY".to_string(),
                        timestamp: chrono::Utc::now().to_rfc3339(),
                        host: host_name_registry.clone(),
                        host_ip: "10.0.1.50".to_string(),
                        environment: "production".to_string(), 
                        pid: 0,
                        uid: 0, 
                        payload: serde_json::json!({
                            "hive": event.hive,
                            "key_path": event.key_path,
                            "value_name": event.value_name,
                        }),
                    };
                    let _ = tx_registry.send(telemetry).await;
                }
            }
        });

        info!("Windows Sensor is actively monitoring WMI events. Press Ctrl+C to exit.");
        tokio::signal::ctrl_c().await.unwrap();
    }
    
    Ok(())
}
