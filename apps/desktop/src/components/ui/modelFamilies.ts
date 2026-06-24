export function getModelFamily(id: string): string {
  if (id.startsWith("claude")) return "Claude";
  if (id.startsWith("gemini")) return "Gemini";
  if (id.startsWith("gpt-image") || id.startsWith("gpt-image/") || id.startsWith("gpt/gpt-image"))
    return "GPT Image";
  if (id.startsWith("gpt")) return "GPT";
  if (id.startsWith("flux")) return "Flux";
  if (id.startsWith("google/")) return "Google";
  if (id.startsWith("seedream/")) return "Seedream";
  if (id.startsWith("grok-imagine")) return "Grok";
  if (id.startsWith("ideogram/")) return "Ideogram";
  if (id.startsWith("qwen")) return "Qwen";
  if (id.startsWith("wan/")) return "Wan";
  if (id.startsWith("kling")) return "Kling";
  if (id.startsWith("bytedance/")) return "Seedance";
  return "Other";
}
