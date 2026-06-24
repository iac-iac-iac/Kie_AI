import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/Button";
import type { GenerationRecord } from "../../../lib/api";
import { audioDisplayTitle } from "../lib/display";

export function AudioGallery({
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

  if (generations.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="text-3xl opacity-40" aria-hidden>
          ♪
        </div>
        <p className="text-sm text-muted">{t("audio.emptyGallery")}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 overflow-y-auto p-3">
      {generations.map((gen) => (
        <div
          key={gen.id}
          className={`group relative cursor-pointer rounded-xl border p-3 transition-colors hover:bg-[var(--hover-bg)] ${
            selectedId === gen.id
              ? "border-accent ring-2 ring-[var(--accent-ring)]"
              : "border-[var(--glass-border)]"
          }`}
          onClick={() => onSelect(gen.id)}
        >
          <p className="truncate text-sm font-medium text-primary">
            {audioDisplayTitle(gen)}
          </p>
          <p className="mt-1 text-xs text-muted">
            {gen.status === "pending" || gen.status === "running"
              ? "…"
              : new Date(gen.created_at).toLocaleString()}
          </p>
          <Button
            type="button"
            variant="outline"
            className="absolute top-2 right-2 hidden px-2 py-0.5 text-xs group-hover:block"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(gen.id);
            }}
          >
            {t("audio.delete")}
          </Button>
        </div>
      ))}
    </div>
  );
}
