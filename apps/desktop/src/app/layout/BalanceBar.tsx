import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { isSseDegraded } from "../../lib/events";
import { useApiReady } from "../../hooks/useApiReady";
import { Button } from "../../components/ui/Button";

export function BalanceBar() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { isReady, isLoading, lockReason, hasKey } = useApiReady();

  const credits = useQuery({
    queryKey: ["credits"],
    queryFn: () => api.getCredits(),
    enabled: hasKey,
    refetchInterval: isSseDegraded() ? 60_000 : 300_000,
    retry: false,
  });

  const renderValue = () => {
    if (isLoading) {
      return <span className="text-muted">{t("balance.loading")}</span>;
    }
    if (lockReason === "no-key") {
      return <span className="text-subtle">{t("balance.noKey")}</span>;
    }
    if (lockReason === "invalid-key") {
      return <span className="text-status-warn">{t("balance.errorAuth")}</span>;
    }
    if (lockReason === "network") {
      return <span className="text-status-warn">{t("balance.errorNetwork")}</span>;
    }
    if (!isReady) {
      return <span className="text-muted">{t("balance.loading")}</span>;
    }
    if (credits.isError) {
      const err = credits.error;
      if (err instanceof ApiError && err.status === 401) {
        return <span className="text-status-warn">{t("balance.errorAuth")}</span>;
      }
      return <span className="text-status-warn">{t("balance.errorNetwork")}</span>;
    }
    return (
      <span className="text-status-ok font-semibold">
        {t("balance.credits", { count: credits.data?.credits.toLocaleString() ?? "0" })}
      </span>
    );
  };

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-subtle">{t("balance.label")}:</span>
      {renderValue()}
      <Button
        variant="ghost"
        className="h-8 px-2 text-xs"
        title={t("balance.refresh")}
        onClick={() => {
          void queryClient.invalidateQueries({ queryKey: ["has-api-key"] });
          void queryClient.invalidateQueries({ queryKey: ["credits"] });
        }}
      >
        ↻
      </Button>
    </div>
  );
}
