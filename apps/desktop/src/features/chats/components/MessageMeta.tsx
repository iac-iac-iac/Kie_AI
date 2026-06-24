import { useTranslation } from "react-i18next";

interface MessageMetaProps {
  tokensIn?: number | null;
  tokensOut?: number | null;
  credits?: number | null;
}

export function MessageMeta({ tokensIn, tokensOut, credits }: MessageMetaProps) {
  const { t } = useTranslation();
  if (tokensIn == null && tokensOut == null && credits == null) return null;

  return (
    <p className="mt-2 text-xs text-subtle">
      {tokensIn != null && (
        <span>
          {t("chats.tokensIn", { count: tokensIn })}
          {" · "}
        </span>
      )}
      {tokensOut != null && (
        <span>
          {t("chats.tokensOut", { count: tokensOut })}
          {" · "}
        </span>
      )}
      {credits != null && credits > 0 && (
        <span>{t("chats.creditsUsed", { credits: credits.toFixed(2) })}</span>
      )}
    </p>
  );
}
