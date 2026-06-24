import { revealItemInDir } from "@tauri-apps/plugin-opener";
import type { GenerationRecord } from "./api";
import { showToast } from "./toast";

export async function revealGenerationInExplorer(
  generation: GenerationRecord,
  noFileMessage: string,
  errorMessage: string,
): Promise<void> {
  if (!generation.has_file || !generation.local_path) {
    showToast(noFileMessage);
    return;
  }

  try {
    await revealItemInDir(generation.local_path);
  } catch {
    showToast(errorMessage);
  }
}
