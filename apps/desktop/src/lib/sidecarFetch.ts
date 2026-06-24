import { isTauri } from "@tauri-apps/api/core";
import { fetch as tauriFetch } from "@tauri-apps/plugin-http";

/**
 * Fetch sidecar HTTP endpoints. In production the WebView runs on https://tauri.localhost
 * and cannot use window.fetch to http://127.0.0.1 (mixed content). Tauri HTTP plugin bypasses that.
 */
export async function sidecarFetch(
  input: string,
  init?: RequestInit,
): Promise<Response> {
  if (isTauri()) {
    return tauriFetch(input, init);
  }
  return fetch(input, init);
}
