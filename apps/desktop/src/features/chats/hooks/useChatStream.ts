import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, type ContentBlock } from "../../../lib/api";
import type {
  StreamDonePayload,
  StreamDeltaPayload,
  StreamErrorPayload,
} from "../../../lib/sse";

export function useChatStream(chatId: string | null) {
  const queryClient = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);
  const [streamingText, setStreamingText] = useState("");
  const [thinking, setThinking] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setThinking(false);
  }, []);

  const sendAndStream = useCallback(
    async (content: ContentBlock[], toolsEnabled: boolean) => {
      if (!chatId) return;
      setError(null);
      setStreamingText("");
      setThinking(true);
      setStreaming(true);

      try {
        const { message_id } = await api.sendMessage(chatId, content, toolsEnabled);
        await queryClient.invalidateQueries({ queryKey: ["messages", chatId] });
        await queryClient.invalidateQueries({ queryKey: ["chats"] });

        const controller = new AbortController();
        abortRef.current = controller;

        await api.streamReply(chatId, message_id, (event, data) => {
          if (event === "delta") {
            const payload = data as StreamDeltaPayload;
            setThinking(false);
            setStreamingText((prev) => prev + payload.text);
          } else if (event === "done") {
            const payload = data as StreamDonePayload;
            void queryClient.invalidateQueries({ queryKey: ["messages", chatId] });
            void queryClient.invalidateQueries({ queryKey: ["credits"] });
            if (payload.credits > 0) {
              void queryClient.invalidateQueries({ queryKey: ["session-usage"] });
            }
          } else if (event === "error") {
            const payload = data as StreamErrorPayload;
            setError(payload.message);
          }
        }, { signal: controller.signal, toolsEnabled });
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        setStreaming(false);
        setThinking(false);
        setStreamingText("");
        abortRef.current = null;
      }
    },
    [chatId, queryClient],
  );

  return {
    streamingText,
    thinking,
    streaming,
    error,
    sendAndStream,
    stop,
    clearError: () => setError(null),
  };
}
