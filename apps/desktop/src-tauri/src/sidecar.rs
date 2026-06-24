use std::path::PathBuf;
use std::time::{Duration, Instant};

use tauri::AppHandle;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

const DEFAULT_PORT: u16 = 18765;

pub fn sidecar_url() -> String {
    std::env::var("VITE_SIDECAR_URL").unwrap_or_else(|_| format!("http://127.0.0.1:{DEFAULT_PORT}"))
}

pub fn http_client() -> Result<reqwest::blocking::Client, String> {
    reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(8))
        .no_proxy()
        .build()
        .map_err(|e| e.to_string())
}

pub fn data_dir() -> PathBuf {
    std::env::var("KIE_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            std::env::var("APPDATA")
                .map(PathBuf::from)
                .unwrap_or_else(|_| PathBuf::from("."))
                .join("KieAI")
        })
}

fn sidecar_is_healthy(url: &str) -> bool {
    let client = match http_client() {
        Ok(client) => client,
        Err(_) => return false,
    };
    let health = client.get(format!("{url}/health")).send();
    match health {
        Ok(response) if response.status().is_success() => true,
        _ => false,
    }
}

pub fn stop_sidecar() -> Result<(), String> {
    let mut guard = crate::SIDECAR_CHILD
        .lock()
        .map_err(|_| "Sidecar lock poisoned".to_string())?;
    if let Some(child) = guard.take() {
        let _ = child.kill();
    }
    Ok(())
}

fn sidecar_ready_timeout() -> Duration {
    if cfg!(debug_assertions) {
        Duration::from_secs(15)
    } else {
        Duration::from_secs(120)
    }
}

fn wait_for_sidecar_healthy(url: &str) -> bool {
    let deadline = Instant::now() + sidecar_ready_timeout();
    while Instant::now() < deadline {
        if sidecar_is_healthy(url) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    false
}

pub fn ensure_sidecar_started(app: &AppHandle) -> Result<(), String> {
    let url = sidecar_url();
    if sidecar_is_healthy(&url) {
        return Ok(());
    }

    if cfg!(debug_assertions) {
        return Err(format!(
            "Sidecar is not running at {url}. Start dev mode with .\\scripts\\dev.ps1"
        ));
    }

    let sidecar = app
        .shell()
        .sidecar("kie-sidecar")
        .map_err(|e| format!("Failed to resolve sidecar binary: {e}"))?;

    let data = data_dir();
    let (mut rx, child) = sidecar
        .env("KIE_DATA_DIR", data.to_string_lossy().to_string())
        .env("KIE_PORT", DEFAULT_PORT.to_string())
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {e}"))?;

    if let Ok(mut guard) = crate::SIDECAR_CHILD.lock() {
        *guard = Some(child);
    }

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            if let CommandEvent::Error(err) = event {
                eprintln!("sidecar error: {err}");
                break;
            }
        }
    });

    if wait_for_sidecar_healthy(&url) {
        return Ok(());
    }

    Err(format!("Sidecar did not become ready at {url}"))
}

pub fn reload_sidecar_api_key_at(api_key: &str, base_url: &str) -> Result<(), String> {
    let url = base_url.trim_end_matches('/');
    let client = http_client()?;

    let mut last_error = String::new();
    for attempt in 0..3 {
        match client
            .post(format!("{url}/internal/reload-api-key"))
            .json(&serde_json::json!({ "api_key": api_key }))
            .send()
        {
            Ok(response) if response.status().is_success() => return Ok(()),
            Ok(response) => {
                last_error = format!("Sidecar reload failed: HTTP {}", response.status());
            }
            Err(e) => {
                last_error = format!("Failed to reach sidecar at {url}: {e}");
            }
        }
        if attempt < 2 {
            std::thread::sleep(Duration::from_millis(400));
        }
    }
    Err(last_error)
}
