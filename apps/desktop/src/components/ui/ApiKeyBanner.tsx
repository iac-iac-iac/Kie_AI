import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { apiLockMessageKey, useApiReady } from "../../hooks/useHasApiKey";

export function ApiKeyBanner() {
  const { t } = useTranslation();
  const location = useLocation();
  const { isReady, isLoading, lockReason } = useApiReady();

  if (isLoading || isReady || location.pathname === "/settings") {
    return null;
  }

  return (
    <div className="mx-4 mb-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-primary">
      <p>{t(apiLockMessageKey(lockReason))}</p>
      <Link
        to="/settings"
        className="mt-1 inline-block font-medium text-accent underline-offset-2 hover:underline"
      >
        {t("apiKey.goToSettings")}
      </Link>
    </div>
  );
}
