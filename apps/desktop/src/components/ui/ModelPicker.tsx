import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatModelLabel } from "../../lib/modelCapabilities";
import { groupWithFavorites } from "../../lib/favoriteModels";
import { cn } from "../../lib/utils";
import { FavoriteStar } from "./FavoriteStar";
import { getModelFamily } from "./modelFamilies";

export interface ModelPickerItem {
  id: string;
  display_name: string;
  price_hint: string;
  price_updated_at?: string | null;
  estimate_credits?: number | null;
  supports_vision?: boolean;
  supports_tools?: boolean;
}

function ModelRow({
  model,
  selected,
  disabled,
  compact,
  onSelect,
  onFavoriteChange,
}: {
  model: ModelPickerItem;
  selected: boolean;
  disabled?: boolean;
  compact?: boolean;
  onSelect: () => void;
  onFavoriteChange: () => void;
}) {
  const { t } = useTranslation();

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border px-3 py-2 text-left transition-colors",
        compact ? "py-1.5" : "py-2.5",
        selected
          ? "border-accent bg-[var(--accent-muted)]"
          : "border-[var(--glass-border)] hover:border-[var(--accent-ring)] hover:bg-[var(--hover-bg)]",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="min-w-0 flex-1 text-sm font-medium text-primary">
          {formatModelLabel(model.id, model.display_name, t)}
        </span>
        <div className="flex shrink-0 items-center gap-1">
          <FavoriteStar
            modelId={model.id}
            disabled={disabled}
            onToggled={onFavoriteChange}
          />
          <span
            className="text-xs text-subtle"
            title={
              model.price_updated_at
                ? t("models.priceUpdated", {
                    date: new Date(model.price_updated_at).toLocaleString(),
                  })
                : undefined
            }
          >
            {model.price_hint}
          </span>
        </div>
      </div>
      {(model.supports_vision || model.supports_tools) && (
        <div className="mt-1 flex flex-wrap gap-1">
          {model.supports_vision && (
            <span className="rounded bg-[var(--accent-muted)] px-1.5 py-0.5 text-[10px] text-accent">
              {t("chats.badgeVision")}
            </span>
          )}
          {model.supports_tools && (
            <span className="rounded bg-[var(--accent-muted)] px-1.5 py-0.5 text-[10px] text-accent">
              {t("chats.badgeTools")}
            </span>
          )}
        </div>
      )}
    </button>
  );
}

export function ModelPicker({
  models,
  value,
  onChange,
  disabled,
  compact = false,
  label,
}: {
  models: ModelPickerItem[];
  value: string;
  onChange: (modelId: string) => void;
  disabled?: boolean;
  compact?: boolean;
  label?: string;
}) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [favTick, setFavTick] = useState(0);
  const showSearch = models.length >= 5;

  const { favorites, familyGroups } = useMemo(() => {
    void favTick;
    const filtered = query.trim()
      ? models.filter(
          (m) =>
            m.display_name.toLowerCase().includes(query.toLowerCase()) ||
            m.id.toLowerCase().includes(query.toLowerCase()),
        )
      : models;

    const { favorites: favs, rest } = groupWithFavorites(filtered);
    const groups = new Map<string, ModelPickerItem[]>();
    for (const model of rest) {
      const family = getModelFamily(model.id);
      const list = groups.get(family) ?? [];
      list.push(model);
      groups.set(family, list);
    }
    return {
      favorites: favs,
      familyGroups: [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)),
    };
  }, [models, query, favTick]);

  return (
    <div className="flex flex-col gap-2">
      {label && (
        <span className="text-sm font-medium text-primary">{label}</span>
      )}
      {showSearch && (
        <input
          type="search"
          className="input-field"
          placeholder={t("common.searchModels")}
          value={query}
          disabled={disabled}
          onChange={(e) => setQuery(e.target.value)}
        />
      )}
      <div
        className={cn(
          "flex flex-col gap-3",
          compact && "max-h-48 overflow-y-auto",
          !compact && "max-h-72 overflow-y-auto",
        )}
      >
        {favorites.length === 0 && familyGroups.length === 0 && (
          <p className="text-sm text-muted">{t("common.noModelsFound")}</p>
        )}
        {favorites.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-semibold tracking-wide text-subtle uppercase">
              {t("models.favorites")}
            </p>
            <div className={cn("flex flex-col gap-1.5", compact && "gap-1")}>
              {favorites.map((model) => (
                <ModelRow
                  key={`fav-${model.id}`}
                  model={model}
                  selected={model.id === value}
                  disabled={disabled}
                  compact={compact}
                  onSelect={() => onChange(model.id)}
                  onFavoriteChange={() => setFavTick((n) => n + 1)}
                />
              ))}
            </div>
          </div>
        )}
        {familyGroups.map(([family, items]) => (
          <div key={family}>
            <p className="mb-1.5 text-xs font-semibold tracking-wide text-subtle uppercase">
              {family}
            </p>
            <div className={cn("flex flex-col gap-1.5", compact && "gap-1")}>
              {items.map((model) => (
                <ModelRow
                  key={model.id}
                  model={model}
                  selected={model.id === value}
                  disabled={disabled}
                  compact={compact}
                  onSelect={() => onChange(model.id)}
                  onFavoriteChange={() => setFavTick((n) => n + 1)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
