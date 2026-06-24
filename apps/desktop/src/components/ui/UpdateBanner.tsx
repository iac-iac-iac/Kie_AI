import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "./Button";
import {
  checkForUpdate,
  downloadAndInstallUpdate,
  isTauriRuntime,
  markUpdateChecked,
  shouldCheckForUpdates,
} from "../../lib/updater";

export function UpdateBanner() {
  const { t } = useTranslation();
  const [version, setVersion] = useState<string | null>(null);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    if (!isTauriRuntime() || !shouldCheckForUpdates()) return;

    void (async () => {
      markUpdateChecked();
      const info = await checkForUpdate();
      if (info) setVersion(info.version);
    })();
  }, []);

  if (!version) return null;

  return (
    <div className="mx-4 mb-2 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-accent/40 bg-[var(--accent-muted)] px-4 py-2 text-sm">
      <span>{t("updater.banner", { version })}</span>
      <Button
        variant="outline"
        className="h-8 px-3 text-xs"
        disabled={installing}
        onClick={() => {
          setInstalling(true);
          void downloadAndInstallUpdate().finally(() => setInstalling(false));
        }}
      >
        {installing ? t("updater.installing") : t("updater.install")}
      </Button>
    </div>
  );
}
