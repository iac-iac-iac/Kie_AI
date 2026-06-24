import { useTranslation } from "react-i18next";
import type { MessageRecord } from "../../../lib/api";
import { blocksToText } from "../../../lib/chatContent";
import { showToast } from "../../../lib/toast";
import { cn } from "../../../lib/utils";
import { MarkdownContent } from "./MarkdownContent";
import { MessageMeta } from "./MessageMeta";

interface MessageBubbleProps {
  message: MessageRecord;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const { t } = useTranslation();
  const isUser = message.role === "user";
  const text = blocksToText(message.content);
  const images = message.content.filter((b) => b.type === "image_url" && b.url);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      showToast(t("chats.copied"));
    } catch {
      showToast(t("chats.copy"));
    }
  };

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "group relative max-w-[85%] rounded-2xl px-4 py-3 text-sm",
          isUser
            ? "bg-accent text-white"
            : "glass-panel border border-[var(--glass-border)]",
        )}
      >
        {images.map((img) => (
          <img
            key={img.url}
            src={img.url}
            alt=""
            className="mb-2 max-h-48 rounded-lg object-contain"
          />
        ))}
        {isUser ? (
          <p className="whitespace-pre-wrap">{text}</p>
        ) : (
          <>
            <button
              type="button"
              className="absolute right-2 top-2 rounded px-2 py-0.5 text-xs text-muted opacity-0 transition-opacity hover:text-primary group-hover:opacity-100"
              onClick={() => void handleCopy()}
              title={t("chats.copy")}
            >
              {t("chats.copy")}
            </button>
            <div className="prose-invert text-primary">
              <MarkdownContent content={text} />
            </div>
          </>
        )}
        {!isUser && (
          <MessageMeta
            tokensIn={message.tokens_in}
            tokensOut={message.tokens_out}
            credits={message.credits}
          />
        )}
      </div>
    </div>
  );
}

interface StreamingBubbleProps {
  text: string;
}

export function StreamingBubble({ text }: StreamingBubbleProps) {
  return (
    <div className="flex justify-start">
      <div className="glass-panel max-w-[85%] rounded-2xl border border-[var(--glass-border)] px-4 py-3 text-sm">
        <div className="text-primary">
          <MarkdownContent content={text || "▍"} />
        </div>
      </div>
    </div>
  );
}
