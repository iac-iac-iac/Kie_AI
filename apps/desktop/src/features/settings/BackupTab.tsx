import { useMutation, useQueryClient } from "@tanstack/react-query";
import { invoke } from "@tauri-apps/api/core";
import { save, open } from "@tauri-apps/plugin-dialog";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/ui/Button";
import { Card, CardTitle } from "../../components/ui/Card";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { Switch } from "../../components/ui/Switch";
import { getSidecarUrl } from "../../lib/sidecar";
import { showToast } from "../../lib/toast";

export function BackupTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [includeMedia, setIncludeMedia] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [pendingImportPath, setPendingImportPath] = useState<string | null>(null);

  const exportBackup = useMutation({
    mutationFn: async () => {
      const dest = await save({
        title: t("backup.exportDialogTitle"),
        filters: [{ name: t("backup.fileFilter"), extensions: ["zip"] }],
        defaultPath: `kie-backup-${new Date().toISOString().slice(0, 10)}.zip`,
      });
      if (!dest) return;
      const sidecarUrl = await getSidecarUrl();
      await invoke("export_backup", {
        destPath: dest,
        includeMedia,
        sidecarUrl,
      });
      showToast(t("backup.exportSuccess"));
    },
    onError: (err) => {
      showToast(`${t("backup.exportFailed")}: ${String(err)}`);
    },
  });

  const importBackup = useMutation({
    mutationFn: async (srcPath: string) => {
      await invoke("import_backup", { srcPath });
      await queryClient.invalidateQueries();
      showToast(t("backup.importSuccess"));
    },
    onError: (err) => {
      showToast(`${t("backup.importFailed")}: ${String(err)}`);
    },
    onSettled: () => {
      setImportOpen(false);
      setPendingImportPath(null);
    },
  });

  const pickImport = async () => {
    const selected = await open({
      title: t("backup.importDialogTitle"),
      filters: [{ name: t("backup.fileFilter"), extensions: ["zip"] }],
      multiple: false,
    });
    if (!selected || Array.isArray(selected)) return;
    setPendingImportPath(selected);
    setImportOpen(true);
  };

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardTitle>{t("settings.tabs.backup")}</CardTitle>
        <p className="mt-2 text-sm text-muted">{t("backup.description")}</p>
        <p className="mt-1 text-sm text-subtle">{t("backup.noApiKey")}</p>

        <div className="mt-4">
          <Switch
            checked={includeMedia}
            onChange={setIncludeMedia}
            label={t("backup.includeMedia")}
          />
          {includeMedia && (
            <p className="mt-2 text-xs text-amber-400">{t("backup.includeMediaWarning")}</p>
          )}
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <Button
            disabled={exportBackup.isPending}
            onClick={() => void exportBackup.mutate()}
          >
            {exportBackup.isPending ? t("backup.exporting") : t("backup.export")}
          </Button>
          <Button
            variant="outline"
            disabled={importBackup.isPending}
            onClick={() => void pickImport()}
          >
            {importBackup.isPending ? t("backup.importing") : t("backup.import")}
          </Button>
        </div>
      </Card>

      <ConfirmDialog
        open={importOpen}
        title={t("backup.importConfirmTitle")}
        message={t("backup.importConfirmMessage")}
        confirmLabel={t("backup.import")}
        cancelLabel={t("common.cancel")}
        destructive
        loading={importBackup.isPending}
        onConfirm={() => {
          if (pendingImportPath) void importBackup.mutate(pendingImportPath);
        }}
        onCancel={() => {
          setImportOpen(false);
          setPendingImportPath(null);
        }}
      />
    </div>
  );
}
