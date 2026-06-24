import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";

export function CostEstimateBar({
  estimateCredits,
  priceHint,
  onSessionBlockedChange,
}: {
  estimateCredits?: number | null;
  priceHint: string;
  onSessionBlockedChange?: (blocked: boolean) => void;
}) {
  const { t } = useTranslation();

  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.getSettings(),
  });

  const sessionEnabled = settings.data?.session_limit_enabled === true;

  const usage = useQuery({
    queryKey: ["session-usage"],
    queryFn: () => api.getSessionUsage(),
    enabled: sessionEnabled,
    refetchInterval: 30_000,
  });

  const estimate = estimateCredits ?? null;
  const costLabel =
    estimate != null
      ? t("generation.costEstimate", { credits: estimate })
      : priceHint;

  const spent = usage.data?.spent ?? 0;
  const limit = usage.data?.limit ?? settings.data?.session_limit_credits ?? null;
  const sessionBlocked =
    sessionEnabled &&
    estimate != null &&
    limit != null &&
    spent + estimate > limit;

  useEffect(() => {
    onSessionBlockedChange?.(sessionBlocked);
  }, [sessionBlocked, onSessionBlockedChange]);

  return (
    <div className="space-y-1 text-sm">
      <p className="text-muted">{costLabel}</p>
      {sessionEnabled && limit != null && estimate != null && (
        <p
          className={
            sessionBlocked ? "text-status-error" : "text-subtle"
          }
        >
          {sessionBlocked
            ? t("generation.sessionExceeded", {
                spent: spent.toLocaleString(),
                after: (spent + estimate).toLocaleString(),
                limit: limit.toLocaleString(),
              })
            : t("generation.sessionAfter", {
                spent: spent.toLocaleString(),
                after: (spent + estimate).toLocaleString(),
                limit: limit.toLocaleString(),
              })}
        </p>
      )}
    </div>
  );
}
