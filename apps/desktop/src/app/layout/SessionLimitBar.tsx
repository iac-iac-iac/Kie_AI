import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { isSseDegraded } from "../../lib/events";

export function SessionLimitBar() {
  const { t } = useTranslation();

  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.getSettings(),
  });

  const usage = useQuery({
    queryKey: ["session-usage"],
    queryFn: () => api.getSessionUsage(),
    enabled: settings.data?.session_limit_enabled === true,
    refetchInterval: isSseDegraded() ? 30_000 : 300_000,
  });

  if (!settings.data?.session_limit_enabled || !usage.data?.limit) {
    return null;
  }

  const spent = usage.data.spent;
  const limit = usage.data.limit;
  const percent = Math.min(100, Math.round((spent / limit) * 100));

  return (
    <footer className="glass-panel mx-4 mb-4 rounded-2xl px-4 py-2">
      <div className="flex items-center justify-between text-xs text-muted">
        <span>{t("session.label")}</span>
        <span>{t("session.usage", { spent: spent.toLocaleString(), limit: limit.toLocaleString() })}</span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-black/20">
        <div
          className={`h-full rounded-full transition-all ${percent >= 90 ? "bg-status-error" : "bg-accent"}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </footer>
  );
}
