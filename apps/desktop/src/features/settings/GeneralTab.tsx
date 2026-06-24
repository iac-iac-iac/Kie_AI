import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/ui/Button";
import { Card, CardTitle } from "../../components/ui/Card";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { Input } from "../../components/ui/Input";
import { Switch } from "../../components/ui/Switch";
import { api } from "../../lib/api";
import { getSidecarUrl } from "../../lib/sidecar";
import { useSettingsForm } from "./useSettingsForm";

export function GeneralTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { form, update, saveSettings } = useSettingsForm();
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const hasKeyQuery = useQuery({
    queryKey: ["has-api-key"],
    queryFn: () => invoke<boolean>("has_api_key"),
  });

  const deleteKey = useMutation({
    mutationFn: async () => {
      const sidecarUrl = await getSidecarUrl();
      await invoke("delete_api_key", { sidecarUrl });
    },
    onSuccess: () => {
      setDeleteOpen(false);
      setMessage({ text: t("settings.apiKeyDeleted"), ok: true });
      void queryClient.invalidateQueries({ queryKey: ["has-api-key"] });
      void queryClient.invalidateQueries({ queryKey: ["health"] });
      void queryClient.invalidateQueries({ queryKey: ["credits"] });
      void queryClient.invalidateQueries({ queryKey: ["session-usage"] });
    },
    onError: (err) => {
      setMessage({
        text: `${t("settings.apiKeyDeleteError")}: ${err instanceof Error ? err.message : String(err)}`,
        ok: false,
      });
    },
  });

  const saveApiKey = async () => {
    setMessage(null);
    const trimmed = apiKey.trim();
    if (!trimmed) return;

    try {
      const sidecarUrl = await getSidecarUrl();
      await invoke("save_api_key", { key: trimmed });

      try {
        await invoke("sync_api_key_to_sidecar", { sidecarUrl });
      } catch {
        await api.reloadApiKey(trimmed);
      }

      setApiKey("");
      setMessage({ text: t("settings.apiKeySaved"), ok: true });
      void queryClient.invalidateQueries({ queryKey: ["has-api-key"] });
      void queryClient.invalidateQueries({ queryKey: ["health"] });
      void queryClient.invalidateQueries({ queryKey: ["credits"] });
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      setMessage({ text: `${t("settings.apiKeyError")}: ${detail}`, ok: false });
    }
  };

  const testConnection = async () => {
    setTestResult(null);
    try {
      const result = await api.testConnection();
      if (result.ok) {
        setTestResult(t("settings.testOk", { credits: result.credits ?? 0 }));
        void queryClient.invalidateQueries({ queryKey: ["credits"] });
      } else {
        setTestResult(t("settings.testFail", { error: result.error ?? "unknown" }));
      }
    } catch (err) {
      setTestResult(t("settings.testFail", { error: String(err) }));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardTitle>{t("settings.apiKey")}</CardTitle>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <Input
            type="password"
            className="sm:flex-1"
            placeholder={t("settings.apiKeyPlaceholder")}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            autoComplete="off"
          />
          <Button
            className="shrink-0"
            onClick={() => void saveApiKey()}
            disabled={!apiKey.trim()}
          >
            {t("settings.apiKeySave")}
          </Button>
        </div>
        {message && (
          <p className={`mt-3 text-sm ${message.ok ? "text-status-ok" : "text-status-error"}`}>
            {message.text}
          </p>
        )}
        <div className="mt-4 border-t border-[var(--glass-border)] pt-4">
          <Button
            variant="outline"
            className="border-status-error text-status-error hover:bg-red-500/10"
            disabled={!hasKeyQuery.data || deleteKey.isPending}
            onClick={() => setDeleteOpen(true)}
          >
            {t("settings.apiKeyDelete")}
          </Button>
        </div>
      </Card>

      <ConfirmDialog
        open={deleteOpen}
        title={t("settings.apiKeyDelete")}
        message={t("settings.apiKeyDeleteConfirm")}
        confirmLabel={t("settings.apiKeyDelete")}
        cancelLabel={t("common.cancel")}
        destructive
        loading={deleteKey.isPending}
        onConfirm={() => void deleteKey.mutate()}
        onCancel={() => setDeleteOpen(false)}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardTitle>{t("settings.proxy")}</CardTitle>
          <div className="flex flex-col gap-4">
            <Switch
              checked={form.proxy.enabled}
              onChange={(enabled) => update("proxy", { ...form.proxy, enabled })}
              label={t("settings.proxyEnabled")}
            />
            <Input
              placeholder={t("settings.proxyHint")}
              value={form.proxy.url ?? ""}
              disabled={!form.proxy.enabled}
              onChange={(e) =>
                update("proxy", { ...form.proxy, url: e.target.value || null })
              }
            />
          </div>
        </Card>

        <Card>
          <CardTitle>{t("settings.notifications")}</CardTitle>
          <Switch
            checked={form.notifications_enabled}
            onChange={(v) => update("notifications_enabled", v)}
            label={t("settings.notificationsEnabled")}
          />
        </Card>

        <Card className="md:col-span-2">
          <CardTitle>{t("settings.sessionLimit")}</CardTitle>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <Switch
              checked={form.session_limit_enabled}
              onChange={(v) => update("session_limit_enabled", v)}
              label={t("settings.sessionLimitEnabled")}
            />
            <Input
              type="number"
              className="sm:max-w-xs"
              min={0}
              disabled={!form.session_limit_enabled}
              placeholder={t("settings.sessionLimitCredits")}
              value={form.session_limit_credits ?? ""}
              onChange={(e) =>
                update(
                  "session_limit_credits",
                  e.target.value ? Number(e.target.value) : null,
                )
              }
            />
          </div>
        </Card>
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            onClick={() => void saveSettings.mutateAsync(form)}
            disabled={saveSettings.isPending}
          >
            {t("settings.save")}
          </Button>
          <Button variant="outline" onClick={() => void testConnection()}>
            {t("settings.testConnection")}
          </Button>
          {testResult && <p className="text-muted text-sm">{testResult}</p>}
        </div>
      </Card>
    </div>
  );
}
