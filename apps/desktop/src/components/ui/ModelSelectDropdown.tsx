import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { groupWithFavorites } from "../../lib/favoriteModels";
import { formatModelLabel } from "../../lib/modelCapabilities";
import { cn } from "../../lib/utils";
import type { ModelPickerItem } from "./ModelPicker";
import { FavoriteStar } from "./FavoriteStar";
import { getModelFamily } from "./modelFamilies";

export function ModelSelectDropdown({
  models,
  value,
  onChange,
  disabled,
  label,
}: {
  models: ModelPickerItem[];
  value: string;
  onChange: (modelId: string) => void;
  disabled?: boolean;
  label?: string;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [favTick, setFavTick] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = models.find((m) => m.id === value);

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

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);

  const pick = (modelId: string) => {
    onChange(modelId);
    setOpen(false);
    setQuery("");
  };

  const renderOption = (model: ModelPickerItem) => {
    const isSelected = model.id === value;
    return (
      <div
        key={model.id}
        role="option"
        aria-selected={isSelected}
        className={cn(
          "flex w-full items-center justify-between gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors",
          isSelected
            ? "bg-[var(--accent-muted)] text-primary"
            : "hover:bg-[var(--hover-bg)]",
        )}
      >
        <button
          type="button"
          className="min-w-0 flex-1 truncate text-left font-medium"
          onClick={() => pick(model.id)}
        >
          {formatModelLabel(model.id, model.display_name, t)}
        </button>
        <div className="flex shrink-0 items-center gap-1">
          <FavoriteStar
            modelId={model.id}
            onToggled={() => setFavTick((n) => n + 1)}
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
    );
  };

  return (
    <div ref={rootRef} className={cn("relative", open && "z-50")}>
      {label && (
        <span className="mb-1.5 block text-sm font-medium text-primary">{label}</span>
      )}
      <button
        type="button"
        disabled={disabled}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => {
          if (!disabled) setOpen((prev) => !prev);
        }}
        className={cn(
          "input-field flex w-full items-center justify-between gap-2 text-left",
          disabled && "cursor-not-allowed opacity-50",
        )}
      >
        <span className="min-w-0 truncate">
          {selected ? (
            <>
              <span className="font-medium text-primary">
                {formatModelLabel(selected.id, selected.display_name, t)}
              </span>
              <span className="ml-2 text-subtle">{selected.price_hint}</span>
            </>
          ) : (
            <span className="text-subtle">{t("common.selectModel")}</span>
          )}
        </span>
        <span
          className={cn(
            "shrink-0 text-subtle transition-transform",
            open && "rotate-180",
          )}
          aria-hidden
        >
          ▾
        </span>
      </button>

      {open && (
        <div
          className="glass-dropdown absolute top-full right-0 left-0 z-50 mt-1 flex max-h-72 flex-col overflow-hidden rounded-xl border border-[var(--glass-border)] shadow-xl"
          role="listbox"
        >
          {models.length >= 5 && (
            <div className="border-b border-[var(--glass-border)] p-2">
              <input
                type="search"
                className="input-field"
                placeholder={t("common.searchModels")}
                value={query}
                autoFocus
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          )}
          <div className="overflow-y-auto p-2">
            {favorites.length === 0 && familyGroups.length === 0 ? (
              <p className="px-2 py-3 text-sm text-muted">{t("common.noModelsFound")}</p>
            ) : (
              <>
                {favorites.length > 0 && (
                  <div className="mb-2">
                    <p className="px-2 py-1 text-xs font-semibold tracking-wide text-subtle uppercase">
                      {t("models.favorites")}
                    </p>
                    {favorites.map(renderOption)}
                  </div>
                )}
                {familyGroups.map(([family, items]) => (
                  <div key={family} className="mb-2 last:mb-0">
                    <p className="px-2 py-1 text-xs font-semibold tracking-wide text-subtle uppercase">
                      {family}
                    </p>
                    {items.map(renderOption)}
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
