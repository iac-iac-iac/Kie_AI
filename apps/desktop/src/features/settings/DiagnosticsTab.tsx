import { useQuery } from "@tanstack/react-query";
import { invoke } from "@tauri-apps/api/core";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/ui/Button";
import { Card, CardTitle } from "../../components/ui/Card";
import { api } from "../../lib/api";
import { maskProxyUrl, revealPath } from "../../lib/revealPath";
import { showToast } from "../../lib/toast";
import { cn } from "../../lib/utils";
import { useSettingsForm } from "./useSettingsForm";
import {
  checkForUpdate,
  downloadAndInstallUpdate,
  isTauriRuntime,
} from "../../lib/updater";

type CheckStatus = "ok" | "warn" | "error" | "loading";

function StatusDot({ status }: { status: CheckStatus }) {
  return (
    <span
      className={cn(
        "inline-block h-2.5 w-2.5 shrink-0 rounded-full",
        status === "ok" && "bg-status-ok",
        status === "warn" && "bg-amber-400",
        status === "error" && "bg-status-error",
        status === "loading" && "bg-subtle animate-pulse",
      )}
      aria-hidden
    />
  );
}

export function DiagnosticsTab() {
  const { t } = useTranslation();
  const { form } = useSettingsForm();
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    credits?: number;
    error?: string;
  } | null>(null);
  const [testing, setTesting] = useState(false);
  const [updateStatus, setUpdateStatus] = useState<
    "idle" | "checking" | "current" | "available" | "error"
  >("idle");
  const [updateVersion, setUpdateVersion] = useState<string | null>(null);
  const [installingUpdate, setInstallingUpdate] = useState(false);

  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
    retry: false,
  });

  const paths = useQuery({
    queryKey: ["system-paths"],
    queryFn: () => api.getSystemPaths(),
    retry: false,
  });

  const hasKey = useQuery({
    queryKey: ["has-api-key"],
    queryFn: () => invoke<boolean>("has_api_key"),
  });

  const appVersion = useQuery({
    queryKey: ["app-version"],
    queryFn: () => invoke<string>("get_app_version"),
  });

  const runUpdateCheck = async () => {
    if (!isTauriRuntime()) {
      setUpdateStatus("error");
      return;
    }
    setUpdateStatus("checking");
    setUpdateVersion(null);
    try {
      const info = await checkForUpdate();
      if (info) {
        setUpdateVersion(info.version);
        setUpdateStatus("available");
      } else {
        setUpdateStatus("current");
      }
    } catch {
      setUpdateStatus("error");
    }
  };

  const runTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await api.testConnection();
      setTestResult(result);
    } catch (err) {
      setTestResult({ ok: false, error: String(err) });
    } finally {
      setTesting(false);
    }
  };

  const checks = useMemo((): { id: string; status: CheckStatus; detail: string }[] => {
    const sidecarStatus: CheckStatus = health.isLoading
      ? "loading"
      : health.isError
        ? "error"
        : "ok";

    const keyStatus: CheckStatus = hasKey.isLoading
      ? "loading"
      : hasKey.data
        ? "ok"
        : "warn";

    const kieStatus: CheckStatus = testing
      ? "loading"
      : testResult
        ? testResult.ok
          ? "ok"
          : "error"
        : hasKey.data
          ? "warn"
          : "warn";

    const proxyStatus: CheckStatus = form.proxy.enabled
      ? form.proxy.url
        ? "ok"
        : "warn"
      : "ok";

    const pricingStatus: CheckStatus = health.isLoading
      ? "loading"
      : health.data?.pricing_updated_at
        ? "ok"
        : "warn";

    return [
      {
        id: "sidecar",
        status: sidecarStatus,
        detail:
          health.data?.version != null
            ? t("diagnostics.sidecarVersion", { version: health.data.version })
            : health.error
              ? String(health.error)
              : "—",
      },
      {
        id: "keyring",
        status: keyStatus,
        detail: hasKey.data ? t("diagnostics.keyPresent") : t("diagnostics.keyMissing"),
      },
      {
        id: "kieAuth",
        status: kieStatus,
        detail: testResult
          ? testResult.ok
            ? t("diagnostics.kieOk", { credits: testResult.credits ?? 0 })
            : t("diagnostics.kieFail", { error: testResult.error ?? "unknown" })
          : t("diagnostics.kieNotRun"),
      },
      {
        id: "proxy",
        status: proxyStatus,
        detail: form.proxy.enabled
          ? maskProxyUrl(form.proxy.url) ?? t("diagnostics.proxyMissingUrl")
          : t("diagnostics.proxyOff"),
      },
      {
        id: "appVersion",
        status: appVersion.isLoading ? "loading" : appVersion.isError ? "error" : "ok",
        detail: appVersion.data ?? "—",
      },
      {
        id: "pricingUpdated",
        status: pricingStatus,
        detail: health.data?.pricing_updated_at
          ? t("diagnostics.pricingUpdatedAt", {
              date: new Date(health.data.pricing_updated_at).toLocaleString(),
            })
          : t("diagnostics.pricingNotSynced"),
      },
    ];
  }, [health, hasKey, testResult, testing, form, appVersion, t]);

  const copyReport = async () => {
    const report = {
      generated_at: new Date().toISOString(),
      app_version: appVersion.data ?? null,
      sidecar_version: health.data?.version ?? null,
      sidecar_ok: !health.isError,
      has_api_key: hasKey.data ?? false,
      proxy_enabled: form.proxy.enabled,
      proxy_url: maskProxyUrl(form.proxy.url),
      test_connection: testResult
        ? { ok: testResult.ok, credits: testResult.credits ?? null, error: testResult.error ?? null }
        : null,
      paths: paths.data ?? null,
    };

    try {
      await navigator.clipboard.writeText(JSON.stringify(report, null, 2));
      showToast(t("diagnostics.reportCopied"));
    } catch {
      showToast(t("diagnostics.reportCopyFailed"));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardTitle>{t("settings.tabs.diagnostics")}</CardTitle>
        <ul className="mt-3 flex flex-col gap-3">
          {checks.map((check) => (
            <li key={check.id} className="flex items-start gap-3 text-sm">
              <StatusDot status={check.status} />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-primary">{t(`diagnostics.checks.${check.id}`)}</p>
                <p className="text-subtle break-all">{check.detail}</p>
              </div>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" disabled={testing} onClick={() => void runTest()}>
            {t("settings.testConnection")}
          </Button>
          <Button variant="outline" onClick={() => void copyReport()}>
            {t("diagnostics.copyReport")}
          </Button>
          {isTauriRuntime() && (
            <>
              <Button
                variant="outline"
                disabled={updateStatus === "checking" || installingUpdate}
                onClick={() => void runUpdateCheck()}
              >
                {updateStatus === "checking"
                  ? t("updater.checking")
                  : t("updater.check")}
              </Button>
              {updateStatus === "available" && updateVersion && (
                <Button
                  disabled={installingUpdate}
                  onClick={() => {
                    setInstallingUpdate(true);
                    void downloadAndInstallUpdate().finally(() =>
                      setInstallingUpdate(false),
                    );
                  }}
                >
                  {installingUpdate
                    ? t("updater.installing")
                    : t("updater.install")}
                </Button>
              )}
            </>
          )}
        </div>
        {updateStatus === "current" && (
          <p className="mt-2 text-sm text-status-ok">{t("updater.upToDate")}</p>
        )}
        {updateStatus === "available" && updateVersion && (
          <p className="mt-2 text-sm text-accent">
            {t("updater.available", { version: updateVersion })}
          </p>
        )}
        {updateStatus === "error" && (
          <p className="mt-2 text-sm text-status-warn">{t("updater.error")}</p>
        )}
      </Card>

      {paths.data && (
        <Card>
          <CardTitle>{t("diagnostics.paths")}</CardTitle>
          <ul className="mt-3 flex flex-col gap-2 text-sm">
            {(
              [
                ["data_dir", paths.data.data_dir],
                ["db_path", paths.data.db_path],
                ["media_dir", paths.data.media_dir],
                ["logs_dir", paths.data.logs_dir],
              ] as const
            ).map(([key, path]) => (
              <li key={key} className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-muted">{t(`diagnostics.pathLabels.${key}`)}</span>
                <div className="flex min-w-0 items-center gap-2">
                  <code className="max-w-xs truncate text-xs text-subtle">{path}</code>
                  <Button
                    type="button"
                    variant="outline"
                    className="shrink-0 px-2 py-1 text-xs"
                    onClick={() => void revealPath(path, t("diagnostics.openFailed"))}
                  >
                    {t("diagnostics.open")}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
