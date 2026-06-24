use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use tauri::AppHandle;
use zip::write::SimpleFileOptions;
use zip::{ZipArchive, ZipWriter};

use crate::sidecar;

const DB_SCHEMA_VERSION: u32 = 1;

#[derive(Serialize, Deserialize)]
struct BackupManifest {
    app_version: String,
    exported_at: String,
    db_schema_version: u32,
    includes_media: bool,
}

pub fn data_dir() -> PathBuf {
    sidecar::data_dir()
}

fn checkpoint_db(sidecar_url: &str) -> Result<PathBuf, String> {
    let client = sidecar::http_client()?;
    let url = sidecar_url.trim_end_matches('/');
    let response = client
        .post(format!("{url}/internal/checkpoint-db"))
        .send()
        .map_err(|e| format!("Checkpoint request failed: {e}"))?;
    if !response.status().is_success() {
        return Err(format!("Checkpoint failed: HTTP {}", response.status()));
    }
    let body: serde_json::Value = response
        .json()
        .map_err(|e| format!("Invalid checkpoint response: {e}"))?;
    let snapshot = body
        .get("snapshot_path")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "Missing snapshot_path in response".to_string())?;
    Ok(PathBuf::from(snapshot))
}

fn safe_relative_path(base: &Path, relative: &str) -> Result<PathBuf, String> {
    let rel = Path::new(relative);
    if rel.is_absolute() {
        return Err("Invalid path in backup archive".to_string());
    }
    for component in rel.components() {
        if matches!(component, std::path::Component::ParentDir) {
            return Err("Path traversal in backup archive".to_string());
        }
    }
    let joined = base.join(rel);
    let base_canon = fs::canonicalize(base).map_err(|e| e.to_string())?;
    if let Some(parent) = joined.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let joined_canon = joined.canonicalize().map_err(|e| e.to_string())?;
    if !joined_canon.starts_with(&base_canon) {
        return Err("Path escapes media directory".to_string());
    }
    Ok(joined)
}

fn add_dir_to_zip(
    zip: &mut ZipWriter<File>,
    dir: &Path,
    prefix: &str,
    options: SimpleFileOptions,
) -> Result<(), String> {
    if !dir.is_dir() {
        return Ok(());
    }
    for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        let name = path
            .file_name()
            .and_then(|n| n.to_str())
            .ok_or_else(|| "Invalid path".to_string())?;
        let zip_path = if prefix.is_empty() {
            name.to_string()
        } else {
            format!("{prefix}/{name}")
        };
        if path.is_dir() {
            add_dir_to_zip(zip, &path, &zip_path, options)?;
        } else {
            let mut file = File::open(&path).map_err(|e| e.to_string())?;
            zip.start_file(format!("media/{zip_path}"), options)
                .map_err(|e| e.to_string())?;
            let mut buffer = Vec::new();
            file.read_to_end(&mut buffer).map_err(|e| e.to_string())?;
            zip.write_all(&buffer).map_err(|e| e.to_string())?;
        }
    }
    Ok(())
}

pub fn export_backup(
    dest_path: &str,
    include_media: bool,
    sidecar_url: &str,
    app_version: &str,
) -> Result<(), String> {
    let snapshot = checkpoint_db(sidecar_url)?;
    let snapshot_parent = snapshot
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| PathBuf::from("."));

    let dest = PathBuf::from(dest_path);
    if let Some(parent) = dest.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    let file = File::create(&dest).map_err(|e| e.to_string())?;
    let mut zip = ZipWriter::new(file);
    let options = SimpleFileOptions::default();

    let mut db_file = File::open(&snapshot).map_err(|e| e.to_string())?;
    zip.start_file("kie.db", options)
        .map_err(|e| e.to_string())?;
    let mut buffer = Vec::new();
    db_file
        .read_to_end(&mut buffer)
        .map_err(|e| e.to_string())?;
    zip.write_all(&buffer).map_err(|e| e.to_string())?;

    let manifest = BackupManifest {
        app_version: app_version.to_string(),
        exported_at: chrono_lite_now(),
        db_schema_version: DB_SCHEMA_VERSION,
        includes_media: include_media,
    };
    let manifest_json = serde_json::to_string_pretty(&manifest).map_err(|e| e.to_string())?;
    zip.start_file("manifest.json", options)
        .map_err(|e| e.to_string())?;
    zip.write_all(manifest_json.as_bytes())
        .map_err(|e| e.to_string())?;

    if include_media {
        let media_dir = data_dir().join("media");
        add_dir_to_zip(&mut zip, &media_dir, "", options)?;
    }

    zip.finish().map_err(|e| e.to_string())?;
    let _ = fs::remove_dir_all(snapshot_parent);
    Ok(())
}

pub fn import_backup(src_path: &str, app: &AppHandle) -> Result<(), String> {
    let src = PathBuf::from(src_path);
    if !src.is_file() {
        return Err("Backup file not found".to_string());
    }

    let file = File::open(&src).map_err(|e| e.to_string())?;
    let mut archive = ZipArchive::new(file).map_err(|e| format!("Invalid backup archive: {e}"))?;

    let mut manifest: Option<BackupManifest> = None;
    let mut db_bytes: Option<Vec<u8>> = None;
    let mut has_media = false;

    for i in 0..archive.len() {
        let mut entry = archive.by_index(i).map_err(|e| e.to_string())?;
        let name = entry.name().to_string();
        if name == "manifest.json" {
            let mut raw = String::new();
            entry.read_to_string(&mut raw).map_err(|e| e.to_string())?;
            manifest = Some(serde_json::from_str(&raw).map_err(|e| e.to_string())?);
        } else if name == "kie.db" {
            let mut buf = Vec::new();
            entry.read_to_end(&mut buf).map_err(|e| e.to_string())?;
            db_bytes = Some(buf);
        } else if name.starts_with("media/") {
            has_media = true;
        }
    }

    let manifest = manifest.ok_or_else(|| "Backup manifest missing".to_string())?;
    if manifest.db_schema_version != DB_SCHEMA_VERSION {
        return Err(format!(
            "Unsupported backup schema version: {}",
            manifest.db_schema_version
        ));
    }
    let db_bytes = db_bytes.ok_or_else(|| "Database file missing in backup".to_string())?;

    sidecar::stop_sidecar()?;

    let data = data_dir();
    let db_path = data.join("data").join("kie.db");
    fs::create_dir_all(db_path.parent().unwrap()).map_err(|e| e.to_string())?;

    let temp_db = db_path.with_extension("db.importing");
    fs::write(&temp_db, &db_bytes).map_err(|e| e.to_string())?;
    if db_path.exists() {
        fs::remove_file(&db_path).map_err(|e| e.to_string())?;
    }
    fs::rename(&temp_db, &db_path).map_err(|e| e.to_string())?;

    if has_media && manifest.includes_media {
        let media_dir = data.join("media");
        if media_dir.exists() {
            fs::remove_dir_all(&media_dir).map_err(|e| e.to_string())?;
        }
        fs::create_dir_all(&media_dir).map_err(|e| e.to_string())?;

        let file = File::open(&src).map_err(|e| e.to_string())?;
        let mut archive = ZipArchive::new(file).map_err(|e| e.to_string())?;
        for i in 0..archive.len() {
            let mut entry = archive.by_index(i).map_err(|e| e.to_string())?;
            let name = entry.name().to_string();
            if !name.starts_with("media/") || name.ends_with('/') {
                continue;
            }
            let relative = name.trim_start_matches("media/");
            let out_path = safe_relative_path(&media_dir, relative)?;
            let mut out = File::create(&out_path).map_err(|e| e.to_string())?;
            std::io::copy(&mut entry, &mut out).map_err(|e| e.to_string())?;
        }
    }

    sidecar::ensure_sidecar_started(app).map_err(|e| e.to_string())?;
    Ok(())
}

fn chrono_lite_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("{secs}")
}
