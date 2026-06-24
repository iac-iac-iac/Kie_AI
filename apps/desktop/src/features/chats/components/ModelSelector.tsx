import { useTranslation } from "react-i18next";
import { ModelPicker } from "../../../components/ui/ModelPicker";
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
    <div className="w-full max-w-md">
      <ModelPicker
        label={t("chats.model")}
        models={models}
        value={value}
        onChange={onChange}
        disabled={disabled}
        compact
      />
    </div>
  );
}
