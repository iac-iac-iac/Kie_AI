import { openPath, revealItemInDir } from "@tauri-apps/plugin-opener";
import { showToast } from "./toast";

export async function revealPath(path: string, errorMessage: string): Promise<void> {
  try {
    await revealItemInDir(path);
  } catch {
    try {
      await openPath(path);
    } catch {
      showToast(errorMessage);
    }
  }
}

export function maskProxyUrl(url: string | null | undefined): string | null {
  if (!url?.trim()) return null;
  try {
    const parsed = new URL(url);
    if (parsed.username) parsed.username = "***";
    if (parsed.password) parsed.password = "***";
    return parsed.toString();
  } catch {
    return "***";
  }
}
