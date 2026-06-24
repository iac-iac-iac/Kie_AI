import { useTranslation } from "react-i18next";
import { ModelCatalogGrid } from "../../../components/models/ModelCatalogGrid";
import type { ChatModelInfo } from "../../../lib/api";

interface ModelSelectorProps {
  models: ChatModelInfo[];
  value: string;
  onChange: (modelId: string) => void;
  disabled?: boolean;
}

export function ModelSelector({ models, value, onChange, disabled }: ModelSelectorProps) {
  const { t } = useTranslation();

  return (
    <div className="flex w-full max-w-5xl flex-col gap-3">
      <div className="text-center">
        <h3 className="text-sm font-medium text-primary">{t("chats.model")}</h3>
        <p className="mt-1 text-xs text-muted">{t("models.catalog.subtitle")}</p>
      </div>
      <ModelCatalogGrid
        models={models}
        value={value}
        onChange={onChange}
        disabled={disabled}
      />
    </div>
  );
}
