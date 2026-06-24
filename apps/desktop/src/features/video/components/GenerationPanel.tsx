import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { CostEstimateBar } from "../../../components/generation/CostEstimateBar";
import { ApiKeyLockOverlay } from "../../../components/ui/ApiKeyLockOverlay";
import { Button } from "../../../components/ui/Button";
import { ModelSelectDropdown } from "../../../components/ui/ModelSelectDropdown";
import { api, ApiError } from "../../../lib/api";
import { mapApiError } from "../../../lib/apiErrors";
import type { GenerationDraft } from "../../../lib/generationDraft";
import { showToast } from "../../../lib/toast";
import type { ImageModelInfo } from "../../../lib/api";
import { DynamicModelForm } from "./DynamicModelForm";
import { GenerationStatus } from "./GenerationStatus";
import { useModelSchema } from "../hooks/useVideoModels";
import { useGenerationPoll } from "../../../hooks/useGenerationPoll";
import { useGeneration } from "../hooks/useGenerations";
import { useHotkeys } from "../../../hooks/useHotkeys";

export function GenerationPanel({
  models,
  hasApiKey,
  lockMessageKey = "apiKey.banner",
  onGenerate,
  isGenerating,
  draft,
  onDraftApplied,
}: {
  models: ImageModelInfo[];
  hasApiKey: boolean;
  lockMessageKey?: string;
  onGenerate: (
    modelId: string,
    input: Record<string, unknown>,
  ) => Promise<{ id: string }>;
  isGenerating: boolean;
  draft?: GenerationDraft | null;
  onDraftApplied?: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const [modelId, setModelId] = useState("");
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [formKey, setFormKey] = useState(0);
  const [appliedDraft, setAppliedDraft] = useState<GenerationDraft | null>(null);
  const [activeGenerationId, setActiveGenerationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [sessionBlocked, setSessionBlocked] = useState(false);

  const schemaQuery = useModelSchema(modelId || null);
  const generationQuery = useGeneration(activeGenerationId);
  useGenerationPoll(activeGenerationId, "video");

  useEffect(() => {
    if (models.length > 0 && !modelId) {
      setModelId(models[0].id);
    }
  }, [models, modelId]);

  useEffect(() => {
    if (!draft) return;
    setModelId(draft.modelId);
    setAppliedDraft(draft);
    setFormKey((k) => k + 1);
    onDraftApplied?.();
  }, [draft, onDraftApplied]);

  useEffect(() => {
    if (!appliedDraft?.focusPrompt) return;
    const timer = window.setTimeout(() => {
      promptRef.current?.focus();
      promptRef.current?.select();
    }, 100);
    return () => window.clearTimeout(timer);
  }, [appliedDraft, formKey, schemaQuery.data]);

  const selectedModel = models.find((m) => m.id === modelId);
  const estimateCredits =
    schemaQuery.data?.estimate_credits ?? selectedModel?.estimate_credits ?? null;
  const priceHint = schemaQuery.data?.price_hint ?? selectedModel?.price_hint ?? "";

  const handleGenerate = async () => {
    setError(null);
    if (!modelId) return;
    try {
      const result = await onGenerate(modelId, formValues);
      setActiveGenerationId(result.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        showToast(t("errors.rateLimit"));
      }
      setError(mapApiError(err, t));
    }
  };

  const handleRetry = async () => {
    if (!activeGenerationId) return;
    setRetrying(true);
    setError(null);
    try {
      await api.retryGeneration(activeGenerationId);
      void queryClient.invalidateQueries({ queryKey: ["generation", activeGenerationId] });
      void queryClient.invalidateQueries({ queryKey: ["generations", "video"] });
    } catch (err) {
      setError(mapApiError(err, t));
    } finally {
      setRetrying(false);
    }
  };

  const activeGeneration = generationQuery.data ?? null;
  const showStatus =
    activeGeneration &&
    (activeGeneration.status === "pending" ||
      activeGeneration.status === "running" ||
      activeGeneration.status === "failed" ||
      (activeGeneration.status === "success" && activeGenerationId));

  const canGenerate = hasApiKey && !isGenerating && !!modelId && !sessionBlocked;

  useHotkeys([
    {
      key: "Enter",
      ctrl: true,
      allowInInput: true,
      handler: () => {
        if (canGenerate) void handleGenerate();
      },
    },
  ]);

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {!hasApiKey && <ApiKeyLockOverlay messageKey={lockMessageKey} />}
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          <ModelSelectDropdown
            label={t("video.model")}
            models={models}
            value={modelId}
            onChange={setModelId}
            disabled={!hasApiKey}
          />

          {schemaQuery.data && (
            <div className={!hasApiKey ? "pointer-events-none select-none opacity-40" : undefined}>
              <h3 className="mb-2 text-sm font-medium text-primary">
                {t("video.parameters")}
              </h3>
              <DynamicModelForm
                key={formKey}
                parameters={schemaQuery.data.parameters}
                initialValues={appliedDraft?.values}
                promptRef={promptRef}
                onChange={setFormValues}
                uploadLabelsKey="video"
                promptPlaceholderKey="video.promptPlaceholder"
              />
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-status-error">
              {error}
            </div>
          )}

          {showStatus && activeGeneration && (
            <GenerationStatus
              generation={activeGeneration}
              onRetry={
                activeGeneration.status === "failed" ? () => void handleRetry() : undefined
              }
              retrying={retrying}
            />
          )}
        </div>

        <div className="space-y-3 border-t border-[var(--glass-border)] p-4">
          {hasApiKey && modelId && (
            <CostEstimateBar
              estimateCredits={estimateCredits}
              priceHint={priceHint}
              onSessionBlockedChange={setSessionBlocked}
            />
          )}
          <Button
            type="button"
            className="w-full"
            disabled={!hasApiKey || isGenerating || !modelId || sessionBlocked}
            onClick={() => void handleGenerate()}
          >
            {isGenerating ? t("video.generating") : t("video.generate")}
          </Button>
        </div>
      </div>
    </div>
  );
}
