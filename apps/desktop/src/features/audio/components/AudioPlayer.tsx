import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { GenerationProgressSteps } from "../../../components/generation/GenerationProgressSteps";
import { Button } from "../../../components/ui/Button";
import type { GenerationRecord } from "../../../lib/api";
import { api } from "../../../lib/api";
import { sidecarFetch } from "../../../lib/sidecarFetch";
import { revealGenerationInExplorer } from "../../../lib/revealInExplorer";
import { audioDisplayTitle } from "../lib/display";

function isTextOutput(generation: GenerationRecord): boolean {
  const path = generation.local_path?.toLowerCase() ?? "";
  return path.endsWith(".txt") || path.endsWith(".json");
}

export function AudioPlayer({
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
  const [textContent, setTextContent] = useState<string | null>(null);

  useEffect(() => {
    if (!generation?.has_file) {
      setFileUrl(null);
      setTextContent(null);
      return;
    }
    let cancelled = false;
    void api.getGenerationFileUrl(generation.id).then(async (url) => {
      if (cancelled) return;
      if (isTextOutput(generation)) {
        try {
          const response = await sidecarFetch(url);
          const text = await response.text();
          if (!cancelled) {
            setTextContent(text);
            setFileUrl(null);
          }
        } catch {
          if (!cancelled) setTextContent(null);
        }
        return;
      }
      setTextContent(null);
      setFileUrl(url);
    });
    return () => {
      cancelled = true;
    };
  }, [generation?.id, generation?.has_file, generation?.local_path]);

  if (!generation) return null;

  const isActive =
    generation.status === "pending" || generation.status === "running";
  const canReveal = generation.has_file;
  const canRepeat = generation.status === "success" || generation.status === "failed";
  const isVideo =
    generation.local_path?.toLowerCase().endsWith(".mp4") ?? false;

  return (
    <div className="flex flex-col gap-3">
      {textContent ? (
        <pre className="max-h-64 overflow-auto rounded-xl bg-black/20 p-4 text-sm whitespace-pre-wrap text-primary">
          {textContent}
        </pre>
      ) : fileUrl ? (
        isVideo ? (
          <video src={fileUrl} controls className="w-full rounded-xl" />
        ) : (
          <audio src={fileUrl} controls className="w-full" />
        )
      ) : (
        <div className="flex min-h-24 flex-col items-center justify-center gap-3 rounded-xl bg-black/20 p-4 text-sm text-muted">
          {isActive ? (
            <GenerationProgressSteps
              generation={generation}
              labelsPrefix="audio"
              compact
            />
          ) : (
            <span>
              {generation.status === "failed"
                ? generation.error_msg?.trim() || t("audio.errorUnknown")
                : t("audio.noPreview")}
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
              t("audio.noPreview"),
              t("audio.errorUnknown"),
            )
          }
        >
          {t("generation.revealInExplorer")}
        </Button>
      </div>

      <div className="text-xs text-subtle">
        <p className="font-medium text-primary">{audioDisplayTitle(generation)}</p>
        <p>{generation.model_id}</p>
        {generation.prompt &&
          typeof generation.params?.title === "string" &&
          generation.params.title.trim() && (
          <p className="mt-1 text-primary">{generation.prompt}</p>
        )}
        <p>{new Date(generation.created_at).toLocaleString()}</p>
        {generation.credits_used != null && (
          <p>{t("audio.creditsUsed", { credits: generation.credits_used })}</p>
        )}
      </div>
    </div>
  );
}
