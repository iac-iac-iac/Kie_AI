mod backup;
mod keyring_store;
mod sidecar;

use std::sync::Mutex;

static SIDECAR_CHILD: Mutex<Option<tauri_plugin_shell::process::CommandChild>> = Mutex::new(None);

#[tauri::command]
fn get_sidecar_url() -> String {
    sidecar::sidecar_url()
}

/// Persist API key in Windows Credential Manager only.
#[tauri::command]
fn save_api_key(key: String) -> Result<(), String> {
    let trimmed = key.trim();
    if trimmed.is_empty() {
        return Err("API key cannot be empty".to_string());
    }
    keyring_store::set_api_key(trimmed).map_err(|e| format!("Keyring error: {e}"))
}

/// Push stored API key to the Python sidecar (localhost, no proxy).
#[tauri::command]
fn sync_api_key_to_sidecar(sidecar_url: Option<String>) -> Result<(), String> {
    let key = keyring_store::get_api_key()?.ok_or_else(|| "No API key stored".to_string())?;
    let url = sidecar_url
        .filter(|u| !u.trim().is_empty())
        .unwrap_or_else(|| sidecar::sidecar_url());
    sidecar::reload_sidecar_api_key_at(&key, &url)
}

#[tauri::command]
fn has_api_key() -> Result<bool, String> {
    Ok(keyring_store::get_api_key()?.is_some())
}

#[tauri::command]
fn delete_api_key(sidecar_url: Option<String>) -> Result<(), String> {
    keyring_store::delete_api_key()?;
    let url = sidecar_url
        .filter(|u| !u.trim().is_empty())
        .unwrap_or_else(|| sidecar::sidecar_url());
    sidecar::reload_sidecar_api_key_at("", &url)
}

#[tauri::command]
fn get_app_version(app: tauri::AppHandle) -> String {
    app.package_info().version.to_string()
}

#[tauri::command]
fn export_backup(
    app: tauri::AppHandle,
    dest_path: String,
    include_media: bool,
    sidecar_url: Option<String>,
) -> Result<(), String> {
    let url = sidecar_url
        .filter(|u| !u.trim().is_empty())
        .unwrap_or_else(|| sidecar::sidecar_url());
    let version = app.package_info().version.to_string();
    backup::export_backup(&dest_path, include_media, &url, &version)
}

#[tauri::command]
fn import_backup(app: tauri::AppHandle, src_path: String) -> Result<(), String> {
    backup::import_backup(&src_path, &app)
}

#[tauri::command]
fn stop_sidecar() -> Result<(), String> {
    sidecar::stop_sidecar()
}

#[tauri::command]
fn restart_sidecar(app: tauri::AppHandle, sidecar_url: Option<String>) -> Result<(), String> {
    let _ = sidecar::ensure_sidecar_started(&app);
    let Some(key) = keyring_store::get_api_key()? else {
        return Ok(());
    };
    let url = sidecar_url
        .filter(|u| !u.trim().is_empty())
        .unwrap_or_else(|| sidecar::sidecar_url());
    sidecar::reload_sidecar_api_key_at(&key, &url)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            if let Err(err) = sidecar::ensure_sidecar_started(app.handle()) {
                eprintln!("sidecar start warning: {err}");
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_sidecar_url,
            save_api_key,
            sync_api_key_to_sidecar,
            has_api_key,
            delete_api_key,
            get_app_version,
            export_backup,
            import_backup,
            stop_sidecar,
            restart_sidecar,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
