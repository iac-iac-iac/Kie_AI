import { useTranslation } from "react-i18next";
import { isFavorite, toggleFavorite } from "../../lib/favoriteModels";
import { cn } from "../../lib/utils";

export function FavoriteStar({
  modelId,
  disabled,
  onToggled,
  className,
}: {
  modelId: string;
  disabled?: boolean;
  onToggled?: () => void;
  className?: string;
}) {
  const { t } = useTranslation();
  const active = isFavorite(modelId);

  return (
    <button
      type="button"
      disabled={disabled}
      aria-label={active ? t("models.removeFavorite") : t("models.addFavorite")}
      title={active ? t("models.removeFavorite") : t("models.addFavorite")}
      className={cn(
        "shrink-0 rounded p-0.5 text-base leading-none transition-colors",
        active ? "text-amber-400" : "text-subtle hover:text-amber-400",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
      onClick={(e) => {
        e.stopPropagation();
        e.preventDefault();
        toggleFavorite(modelId);
        onToggled?.();
      }}
    >
      {active ? "★" : "☆"}
    </button>
  );
}
