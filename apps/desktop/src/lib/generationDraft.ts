import type { GenerationRecord } from "./api";

export type GenerationDraft = {
  modelId: string;
  values: Record<string, unknown>;
  focusPrompt?: boolean;
};

export function buildDraftFromGeneration(g: GenerationRecord): GenerationDraft {
  return {
    modelId: g.model_id,
    values: g.params ?? {},
  };
}
