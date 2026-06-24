import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { groupWithFavorites } from "../../lib/favoriteModels";
import { formatModelLabel } from "../../lib/modelCapabilities";
import { cn } from "../../lib/utils";
import type { ModelPickerItem } from "./modelPickerItem";
import { FavoriteStar } from "../ui/FavoriteStar";
import { getModelFamily } from "../ui/modelFamilies";

function sortByPriceThenName(a: ModelPickerItem, b: ModelPickerItem): number {
  const priceA = a.estimate_credits ?? Number.POSITIVE_INFINITY;
  const priceB = b.estimate_credits ?? Number.POSITIVE_INFINITY;
  if (priceA !== priceB) return priceA - priceB;
  return a.display_name.localeCompare(b.display_name, undefined, { sensitivity: "base" });
}

function sortModels(models: ModelPickerItem[]): {
  favorites: ModelPickerItem[];
  groups: [string, ModelPickerItem[]][];
} {
  const { favorites, rest } = groupWithFavorites(models);
  const familyMap = new Map<string, ModelPickerItem[]>();
  for (const model of rest) {
    const family = getModelFamily(model.id);
    const list = familyMap.get(family) ?? [];
    list.push(model);
    familyMap.set(family, list);
  }
  const groups = [...familyMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([family, items]) => [family, [...items].sort(sortByPriceThenName)] as [string, ModelPickerItem[]]);
  return {
    favorites: [...favorites].sort(sortByPriceThenName),
    groups,
  };
}

function ModelCard({
  model,
  selected,
  disabled,
  onSelect,
  onFavoriteChange,
}: {
  model: ModelPickerItem;
  selected: boolean;
  disabled?: boolean;
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
        "glass-panel flex h-full flex-col rounded-xl border p-4 text-left transition-all",
        selected
          ? "border-accent bg-[var(--accent-muted)] ring-1 ring-[var(--accent-ring)]"
          : "border-[var(--glass-border)] hover:border-[var(--accent-ring)] hover:bg-[var(--hover-bg)]",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="line-clamp-2 text-sm font-semibold text-primary">
          {formatModelLabel(model.id, model.display_name, t)}
        </span>
        <FavoriteStar
          modelId={model.id}
          disabled={disabled}
          onToggled={onFavoriteChange}
        />
      </div>
      <p className="mt-2 text-xs text-subtle">{getModelFamily(model.id)}</p>
      <div className="mt-auto flex items-end justify-between gap-2 pt-3">
        <span
          className="text-sm font-medium text-accent"
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
        {model.estimate_credits != null && (
          <span className="text-[10px] text-muted">
            ~{model.estimate_credits} cr
          </span>
        )}
      </div>
      {(model.supports_vision || model.supports_tools) && (
        <div className="mt-2 flex flex-wrap gap-1">
          {model.supports_vision && (
            <span className="rounded bg-[var(--accent-muted)] px-1.5 py-0.5 text-[10px] text-accent">
              {t("chats.badgeVision")}
            </span>
          )}
          {model.supports_tools && (
            <span
              className="rounded bg-[var(--accent-muted)] px-1.5 py-0.5 text-[10px] text-accent"
              title={t("chats.toolsHint")}
            >
              {t("chats.badgeTools")}
            </span>
          )}
        </div>
      )}
    </button>
  );
}

export function ModelCatalogGrid({
  models,
  value,
  onChange,
  disabled,
}: {
  models: ModelPickerItem[];
  value: string;
  onChange: (modelId: string) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [favTick, setFavTick] = useState(0);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return models;
    return models.filter(
      (m) =>
        m.display_name.toLowerCase().includes(q) ||
        m.id.toLowerCase().includes(q) ||
        getModelFamily(m.id).toLowerCase().includes(q),
    );
  }, [models, query]);

  const { favorites, groups } = useMemo(() => {
    void favTick;
    return sortModels(filtered);
  }, [filtered, favTick]);

  const renderSection = (title: string, items: ModelPickerItem[]) => (
    <section key={title} className="space-y-3">
      <h3 className="text-xs font-semibold tracking-wide text-subtle uppercase">{title}</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {items.map((model) => (
          <ModelCard
            key={model.id}
            model={model}
            selected={model.id === value}
            disabled={disabled}
            onSelect={() => onChange(model.id)}
            onFavoriteChange={() => setFavTick((n) => n + 1)}
          />
        ))}
      </div>
    </section>
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <input
        type="search"
        className="input-field max-w-md"
        placeholder={t("common.searchModels")}
        value={query}
        disabled={disabled}
        onChange={(e) => setQuery(e.target.value)}
      />

      <div className="min-h-0 flex-1 space-y-6 overflow-y-auto pb-4">
        {favorites.length === 0 && groups.length === 0 && (
          <p className="text-sm text-muted">{t("common.noModelsFound")}</p>
        )}
        {favorites.length > 0 && renderSection(t("models.favorites"), favorites)}
        {groups.map(([family, items]) => renderSection(family, items))}
      </div>
    </div>
  );
}
