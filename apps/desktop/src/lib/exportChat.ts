import { save } from "@tauri-apps/plugin-dialog";
import { writeTextFile } from "@tauri-apps/plugin-fs";
import { api } from "./api";
import { isTauriRuntime } from "./updater";

export async function exportChatToFile(
  chatId: string,
  defaultTitle: string,
): Promise<boolean> {
  const blob = await api.exportChat(chatId);
  const text = await blob.text();
  const safeName = defaultTitle.replace(/[^\w\s-]/g, "_").slice(0, 80) || "chat";

  if (isTauriRuntime()) {
    const path = await save({
      filters: [{ name: "Markdown", extensions: ["md"] }],
      defaultPath: `${safeName}.md`,
    });
    if (!path) return false;
    await writeTextFile(path, text);
    return true;
  }

  const downloadBlob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(downloadBlob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${safeName}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
  return true;
}
