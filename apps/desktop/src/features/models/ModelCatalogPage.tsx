import { useTranslation } from "react-i18next";
import { Navigate, useLocation, useNavigate, useParams } from "react-router-dom";
import { ModelCatalogGrid } from "../../components/models/ModelCatalogGrid";
import type { ModelCatalogCategory } from "../../components/models/SelectedModelField";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { useCatalogModels } from "./useCatalogModels";

const CATEGORIES: ModelCatalogCategory[] = ["image", "video", "audio"];

const RETURN_PATH: Record<ModelCatalogCategory, string> = {
  image: "/images",
  video: "/video",
  audio: "/audio",
};

export function ModelCatalogPage() {
  const { t } = useTranslation();
  const { category } = useParams<{ category: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { returnTo?: string; selectedId?: string } | null;

  if (!category || !CATEGORIES.includes(category as ModelCatalogCategory)) {
    return <Navigate to="/images" replace />;
  }

  const typedCategory = category as ModelCatalogCategory;
  const { data: models = [], isLoading, isError, refetch } = useCatalogModels(typedCategory);
  const returnTo = state?.returnTo ?? RETURN_PATH[typedCategory];
  const selectedId = state?.selectedId ?? models[0]?.id ?? "";

  const titleKey =
    typedCategory === "image"
      ? "models.catalog.titleImage"
      : typedCategory === "video"
        ? "models.catalog.titleVideo"
        : "models.catalog.titleAudio";

  const handleSelect = (modelId: string) => {
    navigate(returnTo, { state: { modelId } });
  };

  const handleBack = () => {
    navigate(returnTo);
  };

  if (isLoading) {
    return (
      <Card className="mx-auto max-w-2xl text-center">
        <p className="text-muted">{t("models.catalog.loading")}</p>
      </Card>
    );
  }

  return (
    <div className="glass-panel flex h-full min-h-0 flex-col rounded-2xl border border-[var(--glass-border)]">
      <div className="flex items-center gap-3 border-b border-[var(--glass-border)] px-4 py-3">
        <Button type="button" variant="outline" onClick={handleBack}>
          {t("models.catalog.back")}
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-semibold text-primary">{t(titleKey)}</h1>
          <p className="text-xs text-muted">{t("models.catalog.subtitle")}</p>
        </div>
        <span className="shrink-0 text-xs text-subtle">
          {t("models.catalog.count", { count: models.length })}
        </span>
      </div>

      {isError && (
        <div className="border-b border-[var(--glass-border)] bg-red-500/10 px-4 py-3 text-sm text-status-error">
          <p>{t("models.catalog.error")}</p>
          <Button type="button" variant="outline" className="mt-2" onClick={() => void refetch()}>
            {t("models.catalog.retry")}
          </Button>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col p-4">
        <ModelCatalogGrid
          models={models}
          value={selectedId}
          onChange={handleSelect}
        />
      </div>
    </div>
  );
}
