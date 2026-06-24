import { invoke } from "@tauri-apps/api/core";

const DEFAULT_URL = "http://127.0.0.1:18765";

let cachedUrl: string | null = null;

export async function getSidecarUrl(): Promise<string> {
  if (cachedUrl) return cachedUrl;
  try {
    const url = await invoke<string>("get_sidecar_url");
    cachedUrl = url;
  } catch {
    cachedUrl = import.meta.env.VITE_SIDECAR_URL ?? DEFAULT_URL;
  }
  return cachedUrl!;
}
