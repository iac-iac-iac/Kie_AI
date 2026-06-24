import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { BalanceBar } from "./BalanceBar";
import { CustomTitleBar } from "./CustomTitleBar";
import { SessionLimitBar } from "./SessionLimitBar";
import { ApiKeyBanner } from "../../components/ui/ApiKeyBanner";
import { OnboardingModal } from "../../components/onboarding/OnboardingModal";
import { Toast } from "../../components/ui/Toast";
import { UpdateBanner } from "../../components/ui/UpdateBanner";
import { ThemeToggle } from "../../components/ui/ThemeToggle";
import { useHotkeys } from "../../hooks/useHotkeys";
import { useSidecarEvents } from "../../hooks/useSidecarEvents";
import { cn } from "../../lib/utils";

const tabs = [
  { to: "/", key: "chats" },
  { to: "/images", key: "images" },
  { to: "/video", key: "video" },
  { to: "/audio", key: "audio" },
  { to: "/settings", key: "settings" },
] as const;

export function AppShell() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  useSidecarEvents();

  useHotkeys([
    { key: "1", ctrl: true, handler: () => navigate("/") },
    { key: "2", ctrl: true, handler: () => navigate("/images") },
    { key: "3", ctrl: true, handler: () => navigate("/video") },
    { key: "4", ctrl: true, handler: () => navigate("/audio") },
    { key: ",", ctrl: true, handler: () => navigate("/settings") },
  ]);

  return (
    <div className="flex h-full flex-col">
      <CustomTitleBar />

      <header className="glass-panel mx-4 flex items-center justify-between rounded-b-2xl border border-t-0 border-[var(--glass-border)] px-6 py-3">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.to === "/"}
              className={({ isActive }) =>
                cn(
                  "rounded-lg px-4 py-2 text-sm font-medium transition-all",
                  isActive
                    ? "bg-accent text-white shadow-md"
                    : "nav-link-inactive",
                )
              }
            >
              {t(`nav.${tab.key}`)}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <BalanceBar />
        </div>
      </header>

      <ApiKeyBanner />
      <UpdateBanner />

      <main className="flex min-h-0 flex-1 flex-col overflow-hidden p-4 pt-2">
        <Outlet />
      </main>
      <SessionLimitBar />
      <Toast />
      <OnboardingModal />
    </div>
  );
}
