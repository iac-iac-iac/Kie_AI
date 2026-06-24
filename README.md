# Kie AI Desktop

Native desktop client for [kie.ai](https://kie.ai) — chats, image and video generation.

## Prerequisites (Windows 11)

- [Node.js](https://nodejs.org/) 20+
- [Rust](https://www.rust-lang.org/tools/install) (for Tauri)
- [Python](https://www.python.org/) 3.11+
- [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) (usually pre-installed on Windows 11)

## Quick start (development)

```powershell
# Install sidecar dependencies
cd apps/sidecar
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Install desktop dependencies
cd ..\desktop
npm install

# Run both sidecar + Tauri (from repo root)
cd ..\..
.\scripts\dev.ps1
```

## Production build (NSIS installer)

```powershell
# From repo root — builds PyInstaller sidecar + Tauri NSIS .exe
.\scripts\build.ps1
```

Installer output: `apps\desktop\src-tauri\target\release\bundle\nsis\`

**Note:** Unsigned installers may trigger Windows SmartScreen on first run.

### First launch after install

1. Open **Settings** → enter kie.ai API key → **Save**
2. If needed, enable **Proxy** (HTTP/SOCKS5) for access from RF
3. Optional: enable **Session limit** and **Notifications**

The bundled `kie-sidecar` starts automatically with the app.

## Environment

| Variable | Description |
|----------|-------------|
| `KIE_API_KEY` | API key (dev fallback; production uses Windows Credential Manager) |
| `KIE_DATA_DIR` | Data directory (default: `%APPDATA%\KieAI`) |
| `VITE_SIDECAR_URL` | Sidecar URL (default: `http://127.0.0.1:18765`) |

## Project structure

```
apps/desktop/   Tauri 2 + React + TypeScript
apps/sidecar/   Python FastAPI backend
docs/           Architecture & planning
scripts/        Dev & build scripts
```

## Documentation

- [Preliminary plan](docs/01-preliminary-plan.md)
- [Architecture](docs/02-architecture.md)
