import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { useTranslation } from "react-i18next";
import { cn } from "../../lib/utils";

function WindowButton({
  label,
  onClick,
  danger,
  children,
}: {
  label: string;
  onClick: () => void;
  danger?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={cn(
        "flex h-9 w-11 items-center justify-center text-subtle transition-colors hover:bg-[var(--hover-bg)] hover:text-primary",
        danger && "hover:bg-red-500/20 hover:text-status-error",
      )}
    >
      {children}
    </button>
  );
}

export function CustomTitleBar() {
  const { t } = useTranslation();
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    const win = getCurrentWindow();
    void win.isMaximized().then(setIsMaximized);

    let disposed = false;
    void win.onResized(() => {
      void win.isMaximized().then((max) => {
        if (!disposed) setIsMaximized(max);
      });
    });

    return () => {
      disposed = true;
    };
  }, []);

  const minimize = () => {
    void getCurrentWindow().minimize();
  };

  const toggleMaximize = () => {
    void getCurrentWindow().toggleMaximize();
  };

  const close = () => {
    void getCurrentWindow().close();
  };

  return (
    <div className="glass-panel mx-4 mt-2 flex h-9 shrink-0 items-center justify-between overflow-hidden rounded-t-xl border border-b-0 border-[var(--glass-border)]">
      <div
        data-tauri-drag-region
        className="flex h-full min-w-0 flex-1 items-center px-4"
      >
        <span className="truncate text-sm font-semibold text-accent">
          {t("app.title")}
        </span>
      </div>
      <div className="flex shrink-0">
        <WindowButton label={t("window.minimize")} onClick={minimize}>
          <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden>
            <rect x="1" y="4.5" width="8" height="1" fill="currentColor" />
          </svg>
        </WindowButton>
        <WindowButton
          label={isMaximized ? t("window.restore") : t("window.maximize")}
          onClick={toggleMaximize}
        >
          {isMaximized ? (
            <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden>
              <path
                d="M2.5 2.5h4v4H2.5V2.5ZM3.5 3.5v2h2v-2h-2ZM5 5h2.5v2.5H5V5Z"
                fill="currentColor"
              />
            </svg>
          ) : (
            <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden>
              <rect
                x="1.5"
                y="1.5"
                width="7"
                height="7"
                rx="0.5"
                stroke="currentColor"
                strokeWidth="1.2"
                fill="none"
              />
            </svg>
          )}
        </WindowButton>
        <WindowButton label={t("window.close")} onClick={close} danger>
          <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden>
            <path
              d="M1.5 1.5 8.5 8.5M8.5 1.5 1.5 8.5"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeLinecap="round"
            />
          </svg>
        </WindowButton>
      </div>
    </div>
  );
}
