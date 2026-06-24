import type { GenerationRecord } from "../../../lib/api";

export function audioDisplayTitle(generation: GenerationRecord): string {
  const title = generation.params?.title;
  if (typeof title === "string" && title.trim()) {
    return title.trim();
  }
  return generation.prompt?.trim() || generation.model_id;
}
