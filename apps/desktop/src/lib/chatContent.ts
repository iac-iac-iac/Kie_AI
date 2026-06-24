import type { ContentBlock } from "./api";

export function blocksToText(blocks: ContentBlock[]): string {
  return blocks
    .map((b) => {
      if (b.type === "text" && b.text) return b.text;
      if (b.type === "image_url" && b.url) return `![image](${b.url})`;
      if (b.type === "tool_result" && b.content) return b.content;
      return "";
    })
    .filter(Boolean)
    .join("\n\n");
}
