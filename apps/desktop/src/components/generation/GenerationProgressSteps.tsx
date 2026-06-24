import { useTranslation } from "react-i18next";
import type { GenerationRecord } from "../../lib/api";
import { cn } from "../../lib/utils";

export function getActiveStepIndex(generation: GenerationRecord): number {
  if (generation.status === "pending") return 0;
  if (generation.status === "running") {
    if (generation.remote_url && !generation.has_file) return 2;
    return 1;
  }
  return 3;
}

export function GenerationProgressSteps({
  generation,
  labelsPrefix,
  compact = false,
}: {
  generation: GenerationRecord;
  labelsPrefix: "images" | "video" | "audio";
  compact?: boolean;
}) {
  const { t } = useTranslation();
  const activeIndex = getActiveStepIndex(generation);
  const isFailed = generation.status === "failed";
  const isDone = generation.status === "success";

  const steps = [
    t(`${labelsPrefix}.statusPending`),
    t(`${labelsPrefix}.statusRunning`),
    t(`${labelsPrefix}.statusDownloading`),
    isFailed ? t(`${labelsPrefix}.statusFailed`) : t(`${labelsPrefix}.statusSuccess`),
  ];

  if (isDone || isFailed) {
    return null;
  }

  return (
    <ol
      className={cn(
        "flex flex-col",
        compact ? "gap-1.5" : "gap-2",
      )}
    >
      {steps.slice(0, 3).map((label, index) => {
        const isActive = index === activeIndex;
        const isPast = index < activeIndex;

        return (
          <li
            key={label}
            className={cn(
              "flex items-center gap-2",
              compact ? "text-xs" : "text-sm",
              isActive ? "font-medium text-primary" : isPast ? "text-muted" : "text-subtle",
            )}
          >
            {isActive ? (
              <span className="spinner h-3.5 w-3.5 shrink-0" />
            ) : (
              <span
                className={cn(
                  "flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full text-[10px]",
                  isPast
                    ? "bg-accent text-white"
                    : "border border-[var(--glass-border)]",
                )}
                aria-hidden
              >
                {isPast ? "✓" : index + 1}
              </span>
            )}
            <span>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
