import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Input } from "../../../components/ui/Input";
import type { MessageRecord } from "../../../lib/api";
import { MessageBubble, StreamingBubble } from "./MessageBubble";

interface ChatThreadProps {
  messages: MessageRecord[];
  streamingText: string;
  thinking?: boolean;
  messageSearch: string;
  onMessageSearchChange: (value: string) => void;
}

export function ChatThread({
  messages,
  streamingText,
  thinking,
  messageSearch,
  onMessageSearchChange,
}: ChatThreadProps) {
  const { t } = useTranslation();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, thinking]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-[var(--glass-border)] px-4 py-2">
        <Input
          type="search"
          value={messageSearch}
          onChange={(e) => onMessageSearchChange(e.target.value)}
          placeholder={t("chats.searchMessages")}
          aria-label={t("chats.searchMessages")}
        />
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto px-2 py-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {streamingText && <StreamingBubble text={streamingText} />}
        {thinking && !streamingText && (
          <div className="text-sm text-muted">…</div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
