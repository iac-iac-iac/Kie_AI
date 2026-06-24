import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/Button";
import type { ChatModelInfo, ContentBlock } from "../../../lib/api";
import { Switch } from "../../../components/ui/Switch";

interface ChatComposerProps {
  disabled?: boolean;
  streaming?: boolean;
  model?: ChatModelInfo;
  toolsEnabled: boolean;
  onToolsEnabledChange: (value: boolean) => void;
  onSend: (content: ContentBlock[]) => void;
  onStop: () => void;
  onAttachImage?: (file: File) => Promise<string>;
}

export function ChatComposer({
  disabled,
  streaming,
  model,
  toolsEnabled,
  onToolsEnabledChange,
  onSend,
  onStop,
  onAttachImage,
}: ChatComposerProps) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed && !imageUrl) return;
    const content: ContentBlock[] = [];
    if (imageUrl) content.push({ type: "image_url", url: imageUrl });
    if (trimmed) content.push({ type: "text", text: trimmed });
    onSend(content);
    setText("");
    setImageUrl(null);
  };

  const handleFile = async (file: File) => {
    if (!onAttachImage) return;
    setUploading(true);
    try {
      const url = await onAttachImage(file);
      setImageUrl(url);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl border border-[var(--glass-border)] p-4">
      {model?.supports_tools && (
        <div className="mb-3">
          <Switch
            checked={toolsEnabled}
            onChange={onToolsEnabledChange}
            label={t("chats.tools")}
          />
        </div>
      )}

      {imageUrl && (
        <div className="mb-3 flex items-center gap-2">
          <img src={imageUrl} alt="" className="h-16 rounded-lg object-cover" />
          <Button variant="ghost" type="button" onClick={() => setImageUrl(null)}>
            {t("chats.removeImage")}
          </Button>
        </div>
      )}

      <textarea
        className="input-field min-h-[80px] w-full resize-none"
        placeholder={t("chats.inputPlaceholder")}
        value={text}
        disabled={disabled || streaming}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            if (!streaming) handleSend();
          }
        }}
      />

      <div className="mt-3 flex items-center justify-between gap-2">
        <div className="flex gap-2">
          {model?.supports_vision && onAttachImage && (
            <>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void handleFile(file);
                  e.target.value = "";
                }}
              />
              <Button
                type="button"
                variant="outline"
                disabled={disabled || streaming || uploading}
                onClick={() => fileRef.current?.click()}
              >
                {uploading ? t("chats.uploading") : t("chats.attachImage")}
              </Button>
            </>
          )}
        </div>
        <div className="flex gap-2">
          {streaming ? (
            <Button type="button" variant="outline" onClick={onStop}>
              {t("chats.stop")}
            </Button>
          ) : (
            <Button
              type="button"
              disabled={disabled || (!text.trim() && !imageUrl)}
              onClick={handleSend}
            >
              {t("chats.send")}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
