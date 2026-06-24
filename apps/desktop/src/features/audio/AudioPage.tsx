import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { apiLockMessageKey, useApiReady } from "../../hooks/useHasApiKey";
import { useHotkeys } from "../../hooks/useHotkeys";
import { buildDraftFromGeneration, type GenerationDraft } from "../../lib/generationDraft";
import { GenerationPanel } from "./components/GenerationPanel";
import { AudioGallery } from "./components/AudioGallery";
import { AudioPlayer } from "./components/AudioPlayer";
import { useAudioModels } from "./hooks/useAudioModels";
import { useGenerations } from "./hooks/useGenerations";
import { useGenerationPoll } from "../../hooks/useGenerationPoll";

export function AudioPage() {
  const { t } = useTranslation();
  const { isReady: hasApiKey, lockReason } = useApiReady();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<GenerationDraft | null>(null);

  const { models, isLoading, isError, refetch } = useAudioModels();
  const { generations, deleteGeneration, createGeneration } = useGenerations();

  const selectedGeneration =
    generations.find((g) => g.id === selectedId) ?? null;

  const selectedIsActive =
    selectedGeneration?.status === "pending" ||
    selectedGeneration?.status === "running";
  useGenerationPoll(selectedIsActive ? selectedId : null, "audio");

  const handleDelete = async (id: string) => {
    await deleteGeneration.mutateAsync(id);
    if (selectedId === id) setSelectedId(null);
  };

  const openDraft = useCallback((next: GenerationDraft) => {
    setSelectedId(null);
    setDraft(next);
  }, []);

  const handleRepeat = useCallback(() => {
    if (!selectedGeneration) return;
    openDraft(buildDraftFromGeneration(selectedGeneration));
  }, [selectedGeneration, openDraft]);

  const handleVary = useCallback(() => {
    if (!selectedGeneration) return;
    openDraft({ ...buildDraftFromGeneration(selectedGeneration), focusPrompt: true });
  }, [selectedGeneration, openDraft]);

  useHotkeys([
    {
      key: "r",
      ctrl: true,
      handler: () => {
        if (selectedGeneration) handleRepeat();
      },
    },
    {
      key: "Escape",
      handler: () => {
        if (selectedId) setSelectedId(null);
      },
    },
  ]);

  if (isLoading) {
    return (
      <Card className="mx-auto max-w-2xl text-center">
        <p className="text-muted">{t("audio.loading")}</p>
      </Card>
    );
  }

  return (
    <div className="flex h-full min-h-0 gap-4">
      <aside className="glass-panel flex w-[280px] shrink-0 flex-col rounded-2xl border border-[var(--glass-border)]">
        <div className="border-b border-[var(--glass-border)] px-4 py-3">
          <h2 className="text-sm font-medium text-primary">{t("audio.gallery")}</h2>
        </div>
        <AudioGallery
          generations={generations}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onDelete={(id) => void handleDelete(id)}
        />
      </aside>

      <div className="glass-panel flex min-w-0 flex-1 flex-col rounded-2xl border border-[var(--glass-border)]">
        {isError && (
          <div className="border-b border-[var(--glass-border)] bg-red-500/10 px-4 py-3 text-sm text-status-error">
            <p>{t("audio.errorSidecar")}</p>
            <Button
              type="button"
              variant="outline"
              className="mt-2"
              onClick={() => void refetch()}
            >
              {t("audio.retry")}
            </Button>
          </div>
        )}

        {selectedGeneration ? (
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
            <AudioPlayer
              generation={selectedGeneration}
              onRepeat={handleRepeat}
              onVary={handleVary}
            />
          </div>
        ) : (
          <GenerationPanel
            models={models}
            hasApiKey={hasApiKey}
            lockMessageKey={apiLockMessageKey(lockReason)}
            isGenerating={createGeneration.isPending}
            draft={draft}
            onDraftApplied={() => setDraft(null)}
            onGenerate={async (modelId, input) =>
              createGeneration.mutateAsync({ modelId, input })
            }
          />
        )}

        {selectedGeneration && (
          <div className="border-t border-[var(--glass-border)] p-2">
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => setSelectedId(null)}
            >
              {t("audio.newGeneration")}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
