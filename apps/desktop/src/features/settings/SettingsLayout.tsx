import { NavLink, Outlet, Navigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card } from "../../components/ui/Card";
import { cn } from "../../lib/utils";
import { SettingsFormProvider } from "./useSettingsForm";

const tabs = [
  { to: "general", key: "general" },
  { to: "interface", key: "interface" },
  { to: "shortcuts", key: "shortcuts" },
  { to: "diagnostics", key: "diagnostics" },
  { to: "backup", key: "backup" },
  { to: "credits", key: "credits" },
] as const;

export function SettingsLayout() {
  const { t } = useTranslation();
  const location = useLocation();

  if (location.pathname === "/settings" || location.pathname === "/settings/") {
    return <Navigate to="/settings/general" replace />;
  }

  return (
    <SettingsFormProvider>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-4xl flex-col gap-4 pb-6">
          <h1 className="text-xl font-semibold text-primary">{t("settings.title")}</h1>

          <nav className="flex flex-wrap gap-1 rounded-xl border border-[var(--glass-border)] bg-black/10 p-1">
            {tabs.map((tab) => (
              <NavLink
                key={tab.to}
                to={`/settings/${tab.to}`}
                className={({ isActive }) =>
                  cn(
                    "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-accent text-white"
                      : "text-muted hover:bg-[var(--hover-bg)] hover:text-primary",
                  )
                }
              >
                {t(`settings.tabs.${tab.key}`)}
              </NavLink>
            ))}
          </nav>

          <Outlet />
        </div>
      </div>
    </SettingsFormProvider>
  );
}

export function SettingsTabLoading() {
  const { t } = useTranslation();
  return (
    <Card>
      <p className="text-muted">{t("balance.loading")}</p>
    </Card>
  );
}
