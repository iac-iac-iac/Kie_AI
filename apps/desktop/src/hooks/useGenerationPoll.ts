import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { isSseDegraded } from "../lib/events";
import { notifyGenerationComplete } from "../lib/notifications";

const POLL_INTERVAL_MS = 2500;

export function useGenerationPoll(
  generationId: string | null,
  mediaType: "image" | "video" | "audio",
) {
  const queryClient = useQueryClient();
  const notifiedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!generationId) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const pollOnce = async () => {
      try {
        const record = await api.getGeneration(generationId);
        if (cancelled) return;

        void queryClient.setQueryData(["generation", generationId], record);
        void queryClient.invalidateQueries({ queryKey: ["generations", mediaType] });

        if (record.status === "success" || record.status === "failed") {
          void queryClient.invalidateQueries({ queryKey: ["credits"] });
          void queryClient.invalidateQueries({ queryKey: ["session-usage"] });

          if (notifiedRef.current !== generationId) {
            notifiedRef.current = generationId;
            try {
              const settings = await api.getSettings();
              await notifyGenerationComplete(
                settings,
                mediaType,
                record.status,
                record.prompt,
              );
            } catch {
              // ignore notification errors
            }
          }
          return true;
        }
        return false;
      } catch {
        return false;
      }
    };

    const startPolling = () => {
      const poll = async () => {
        const done = await pollOnce();
        if (cancelled || done) return;
        timer = setTimeout(() => void poll(), POLL_INTERVAL_MS);
      };
      void poll();
    };

    void (async () => {
      const done = await pollOnce();
      if (cancelled || done) return;
      if (isSseDegraded()) {
        startPolling();
      }
    })();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [generationId, mediaType, queryClient]);
}
