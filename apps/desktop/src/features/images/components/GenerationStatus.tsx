import { useTranslation } from "react-i18next";
import { GenerationProgressSteps } from "../../../components/generation/GenerationProgressSteps";
import { Button } from "../../../components/ui/Button";
import type { GenerationRecord } from "../../../lib/api";

export function GenerationStatus({
  generation,
  onRetry,
  retrying,
}: {
  generation: GenerationRecord;
  onRetry?: () => void;
  retrying?: boolean;
}) {
  const { t } = useTranslation();

  const isActive = generation.status === "pending" || generation.status === "running";

  return (
    <div className="rounded-xl border border-[var(--glass-border)] bg-black/10 p-4">
      {isActive ? (
        <GenerationProgressSteps generation={generation} labelsPrefix="images" />
      ) : (
        <span className="text-sm font-medium text-primary">
          {generation.status === "success"
            ? t("images.statusSuccess")
            : t("images.statusFailed")}
        </span>
      )}

      {generation.status === "success" && generation.credits_used != null && (
        <p className="mt-2 text-sm text-muted">
          {t("images.creditsUsed", { credits: generation.credits_used })}
        </p>
      )}

      {generation.status === "failed" && (
        <div className="mt-2 flex flex-col gap-2">
          <p className="text-sm text-status-error">
            {generation.error_msg?.trim() || t("images.errorUnknown")}
          </p>
          {onRetry && generation.task_id && (
            <Button
              type="button"
              variant="outline"
              disabled={retrying}
              onClick={onRetry}
            >
              {retrying ? t("images.retrying") : t("images.retryDownload")}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
