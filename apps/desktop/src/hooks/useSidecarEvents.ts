import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getSidecarUrl } from "../lib/sidecar";
import {
  connectSidecarEvents,
  type GenerationUpdatedPayload,
} from "../lib/events";
import { api } from "../lib/api";
import { notifyGenerationComplete } from "../lib/notifications";

const notifiedGenerations = new Set<string>();

async function handleGenerationTerminal(
  record: GenerationUpdatedPayload,
  queryClient: ReturnType<typeof useQueryClient>,
) {
  if (record.status !== "success" && record.status !== "failed") return;
  if (notifiedGenerations.has(record.id)) return;
  notifiedGenerations.add(record.id);

  try {
    const settings = await api.getSettings();
    await notifyGenerationComplete(
      settings,
      record.type,
      record.status,
      record.prompt,
    );
  } catch {
    // ignore notification errors
  }

  void queryClient.invalidateQueries({ queryKey: ["credits"] });
  void queryClient.invalidateQueries({ queryKey: ["session-usage"] });
}

export function useSidecarEvents() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const controller = new AbortController();
    let baseUrl = "";

    const start = async () => {
      baseUrl = await getSidecarUrl();
      connectSidecarEvents(
        baseUrl,
        {
          onGenerationUpdated: (record) => {
            void queryClient.setQueryData(["generation", record.id], record);
            void queryClient.invalidateQueries({
              queryKey: ["generations", record.type],
            });
            void handleGenerationTerminal(record, queryClient);
          },
          onCreditsUpdated: () => {
            void queryClient.invalidateQueries({ queryKey: ["credits"] });
          },
          onSessionUsage: (usage) => {
            void queryClient.setQueryData(["session-usage"], {
              spent: usage.spent,
              limit: usage.limit,
              remaining:
                usage.limit != null ? usage.limit - usage.spent : null,
            });
          },
        },
        controller.signal,
      );
    };

    void start();

    return () => {
      controller.abort();
    };
  }, [queryClient]);
}
