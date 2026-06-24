import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export function ApiKeyLockOverlay({ messageKey }: { messageKey: string }) {
  const { t } = useTranslation();

  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center rounded-2xl bg-[var(--glass-overlay-bg)]/90 p-6 backdrop-blur-sm">
      <div className="max-w-sm text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/15 text-amber-500">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6v-9Z"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <p className="text-sm leading-relaxed text-primary">{t(messageKey)}</p>
        <Link
          to="/settings"
          className="mt-3 inline-flex items-center gap-1 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)]"
        >
          {t("apiKey.goToSettings")}
        </Link>
      </div>
    </div>
  );
}
