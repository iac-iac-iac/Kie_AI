import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { GenerationProgressSteps } from "../../../components/generation/GenerationProgressSteps";
import { Button } from "../../../components/ui/Button";
import type { GenerationRecord } from "../../../lib/api";
import { api } from "../../../lib/api";
import { revealGenerationInExplorer } from "../../../lib/revealInExplorer";

export function VideoPlayer({
  generation,
  onRepeat,
  onVary,
}: {
  generation: GenerationRecord | null;
  onRepeat?: () => void;
  onVary?: () => void;
}) {
  const { t } = useTranslation();
  const [fileUrl, setFileUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!generation?.has_file) {
      setFileUrl(null);
      return;
    }
    let cancelled = false;
    void api.getGenerationFileUrl(generation.id).then((url) => {
      if (!cancelled) setFileUrl(url);
    });
    return () => {
      cancelled = true;
    };
  }, [generation?.id, generation?.has_file]);

  if (!generation) return null;

  const isActive =
    generation.status === "pending" || generation.status === "running";
  const canReveal = generation.has_file;
  const canRepeat = generation.status === "success" || generation.status === "failed";

  return (
    <div className="flex flex-col gap-3">
      {fileUrl ? (
        <video
          src={fileUrl}
          controls
          className="max-h-96 w-full rounded-xl bg-black"
        />
      ) : (
        <div className="flex aspect-video flex-col items-center justify-center gap-3 rounded-xl bg-black/20 p-4 text-sm text-muted">
          {isActive ? (
            <GenerationProgressSteps
              generation={generation}
              labelsPrefix="video"
              compact
            />
          ) : (
            <span>
              {generation.status === "failed"
                ? generation.error_msg?.trim() || t("video.errorUnknown")
                : t("video.noPreview")}
            </span>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {canRepeat && onRepeat && (
          <Button type="button" variant="outline" onClick={onRepeat}>
            {t("generation.repeat")}
          </Button>
        )}
        {canRepeat && onVary && (
          <Button type="button" variant="outline" onClick={onVary}>
            {t("generation.vary")}
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          disabled={!canReveal}
          onClick={() =>
            void revealGenerationInExplorer(
              generation,
              t("video.noPreview"),
              t("video.errorUnknown"),
            )
          }
        >
          {t("generation.revealInExplorer")}
        </Button>
      </div>

      <div className="text-xs text-subtle">
        <p>{generation.model_id}</p>
        {generation.prompt && <p className="mt-1 text-primary">{generation.prompt}</p>}
        <p>{new Date(generation.created_at).toLocaleString()}</p>
        {generation.credits_used != null && (
          <p>{t("video.creditsUsed", { credits: generation.credits_used })}</p>
        )}
      </div>
    </div>
  );
}
