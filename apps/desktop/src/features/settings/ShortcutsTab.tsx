import { useTranslation } from "react-i18next";
import { Card, CardTitle } from "../../components/ui/Card";
import { SHORTCUT_DEFINITIONS } from "../../lib/hotkeys";

export function ShortcutsTab() {
  const { t } = useTranslation();

  return (
    <Card>
      <CardTitle>{t("settings.tabs.shortcuts")}</CardTitle>
      <p className="mb-4 text-sm text-muted">{t("shortcuts.hint")}</p>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--glass-border)] text-left text-subtle">
            <th className="pb-2 pr-4 font-medium">{t("shortcuts.action")}</th>
            <th className="pb-2 font-medium">{t("shortcuts.keys")}</th>
          </tr>
        </thead>
        <tbody>
          {SHORTCUT_DEFINITIONS.map((item) => (
            <tr key={item.id} className="border-b border-[var(--glass-border)] last:border-0">
              <td className="py-2.5 pr-4 text-primary">{t(`shortcuts.${item.id}`)}</td>
              <td className="py-2.5 font-mono text-subtle">{item.keys}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
