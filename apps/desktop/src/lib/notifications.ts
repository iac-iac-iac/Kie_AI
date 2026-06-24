import {
  isPermissionGranted,
  requestPermission,
  sendNotification,
} from "@tauri-apps/plugin-notification";
import type { AppSettings } from "./api";
import i18n from "./i18n";

async function ensurePermission(): Promise<boolean> {
  try {
    let granted = await isPermissionGranted();
    if (!granted) {
      const result = await requestPermission();
      granted = result === "granted";
    }
    return granted;
  } catch {
    return false;
  }
}

export async function notifyGenerationComplete(
  settings: AppSettings,
  type: "image" | "video" | "audio",
  status: "success" | "failed",
  prompt?: string | null,
): Promise<void> {
  if (!settings.notifications_enabled) return;
  if (!(await ensurePermission())) return;

  const label =
    type === "image"
      ? i18n.t("nav.images")
      : type === "video"
        ? i18n.t("nav.video")
        : i18n.t("nav.audio");
  const title =
    status === "success"
      ? i18n.t("notifications.generationSuccess", { type: label })
      : i18n.t("notifications.generationFailed", { type: label });
  const body = prompt?.trim() || undefined;

  try {
    await sendNotification({ title, body });
  } catch {
    // Browser dev mode or unsupported platform
  }
}
