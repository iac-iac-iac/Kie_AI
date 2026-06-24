import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/Button";
import type { GenerationRecord } from "../../../lib/api";
import { api } from "../../../lib/api";

export function ImageGallery({
  generations,
  selectedId,
  onSelect,
  onDelete,
}: {
  generations: GenerationRecord[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const { t } = useTranslation();
  const [urls, setUrls] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const next: Record<string, string> = {};
      for (const gen of generations) {
        if (gen.has_file) {
          next[gen.id] = await api.getGenerationFileUrl(gen.id);
        }
      }
      if (!cancelled) setUrls(next);
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [generations]);

  if (generations.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="text-3xl opacity-40" aria-hidden>
          🖼
        </div>
        <p className="text-sm text-muted">{t("images.emptyGallery")}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2 overflow-y-auto p-3">
      {generations.map((gen) => (
        <div
          key={gen.id}
          className={`group relative aspect-square cursor-pointer overflow-hidden rounded-xl border transition-transform hover:scale-[1.02] ${
            selectedId === gen.id
              ? "border-accent ring-2 ring-[var(--accent-ring)]"
              : "border-[var(--glass-border)] hover:border-[var(--accent-ring)]"
          }`}
          onClick={() => onSelect(gen.id)}
        >
          {urls[gen.id] ? (
            <img
              src={urls[gen.id]}
              alt={gen.prompt ?? ""}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center bg-black/20 text-xs text-muted">
              {gen.status === "pending" || gen.status === "running"
                ? "…"
                : "—"}
            </div>
          )}
          <Button
            type="button"
            variant="outline"
            className="absolute top-1 right-1 hidden px-2 py-0.5 text-xs group-hover:block"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(gen.id);
            }}
          >
            {t("images.delete")}
          </Button>
        </div>
      ))}
    </div>
  );
}
