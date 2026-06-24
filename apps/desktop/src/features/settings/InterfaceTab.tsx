import { useTranslation } from "react-i18next";
import { Button } from "../../components/ui/Button";
import { Card, CardTitle } from "../../components/ui/Card";
import { applyTheme } from "../../lib/theme";
import type { AppSettings } from "../../lib/api";
import { useSettingsForm } from "./useSettingsForm";

export function InterfaceTab() {
  const { t } = useTranslation();
  const { form, update, saveSettings } = useSettingsForm();

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardTitle>{t("settings.interface")}</CardTitle>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-primary flex flex-col gap-2 text-sm">
            {t("settings.theme")}
            <select
              className="select-field"
              value={form.theme}
              onChange={(e) => {
                const theme = e.target.value as AppSettings["theme"];
                update("theme", theme);
                applyTheme(theme);
              }}
            >
              <option value="dark">{t("settings.themeDark")}</option>
              <option value="light">{t("settings.themeLight")}</option>
              <option value="system">{t("settings.themeSystem")}</option>
            </select>
          </label>
          <label className="text-primary flex flex-col gap-2 text-sm">
            {t("settings.locale")}
            <select
              className="select-field"
              value={form.locale}
              onChange={(e) =>
                update("locale", e.target.value as AppSettings["locale"])
              }
            >
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>
      </Card>

      <Card>
        <Button
          onClick={() => void saveSettings.mutateAsync(form)}
          disabled={saveSettings.isPending}
        >
          {t("settings.save")}
        </Button>
      </Card>
    </div>
  );
}
