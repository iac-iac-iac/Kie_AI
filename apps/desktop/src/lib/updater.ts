export interface UpdateInfo {
  version: string;
  currentVersion: string;
}

export async function checkForUpdate(): Promise<UpdateInfo | null> {
  try {
    const { check } = await import("@tauri-apps/plugin-updater");
    const update = await check();
    if (!update) return null;
    return {
      version: update.version,
      currentVersion: update.currentVersion,
    };
  } catch {
    return null;
  }
}

export async function downloadAndInstallUpdate(): Promise<void> {
  const { check } = await import("@tauri-apps/plugin-updater");
  const update = await check();
  if (!update) return;
  await update.downloadAndInstall();
  const { relaunch } = await import("@tauri-apps/plugin-process");
  await relaunch();
}

const LAST_CHECK_KEY = "kie_last_update_check";
const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;

export function shouldCheckForUpdates(): boolean {
  try {
    const raw = localStorage.getItem(LAST_CHECK_KEY);
    if (!raw) return true;
    const last = Number.parseInt(raw, 10);
    if (Number.isNaN(last)) return true;
    return Date.now() - last >= CHECK_INTERVAL_MS;
  } catch {
    return true;
  }
}

export function markUpdateChecked(): void {
  try {
    localStorage.setItem(LAST_CHECK_KEY, String(Date.now()));
  } catch {
    // ignore
  }
}

export function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}
