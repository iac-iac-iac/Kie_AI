import type { TFunction } from "i18next";

const ABBREV_SUFFIX = /\s*(T2V|I2V|T2I|I2I)\s*$/i;

const CAPABILITY_PATTERNS: ReadonlyArray<[string, string]> = [
  ["image-to-video", "models.capability.imageToVideo"],
  ["text-to-video", "models.capability.textToVideo"],
  ["image-to-image", "models.capability.imageToImage"],
  ["text-to-image", "models.capability.textToImage"],
  ["-edit", "models.capability.edit"],
  ["/edit", "models.capability.edit"],
  ["preview", "models.capability.preview"],
];

function capabilityKey(modelId: string): string | null {
  const id = modelId.toLowerCase();
  for (const [pattern, key] of CAPABILITY_PATTERNS) {
    if (id.includes(pattern)) return key;
  }
  return null;
}

export function formatModelLabel(
  modelId: string,
  displayName: string,
  t: TFunction,
): string {
  const key = capabilityKey(modelId);
  if (!key) return displayName;

  const base = displayName.replace(ABBREV_SUFFIX, "").trim();
  return `${base} (${t(key)})`;
}
