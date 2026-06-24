import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { formatModelLabel } from "../../lib/modelCapabilities";
import type { ModelPickerItem } from "./modelPickerItem";
import { Button } from "../ui/Button";

export type ModelCatalogCategory = "image" | "video" | "audio";

export function SelectedModelField({
  models,
  value,
  category,
  disabled,
  label,
}: {
  models: ModelPickerItem[];
  value: string;
  category: ModelCatalogCategory;
  disabled?: boolean;
  label?: string;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const selected = models.find((m) => m.id === value);

  const openCatalog = () => {
    if (disabled) return;
    navigate(`/models/${category}`, {
      state: { returnTo: location.pathname, selectedId: value },
    });
  };

  return (
    <div className="space-y-2">
      {label && <span className="text-sm font-medium text-primary">{label}</span>}
      <div className="flex flex-col gap-2 rounded-xl border border-[var(--glass-border)] bg-[var(--hover-bg)]/40 p-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          {selected ? (
            <>
              <p className="truncate text-sm font-semibold text-primary">
                {formatModelLabel(selected.id, selected.display_name, t)}
              </p>
              <p className="mt-0.5 text-xs text-accent">{selected.price_hint}</p>
            </>
          ) : (
            <p className="text-sm text-muted">{t("common.selectModel")}</p>
          )}
        </div>
        <Button
          type="button"
          variant="outline"
          className="shrink-0"
          disabled={disabled}
          onClick={openCatalog}
        >
          {t("models.catalog.chooseModel")}
        </Button>
      </div>
    </div>
  );
}
