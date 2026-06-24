import type { GenerationRecord } from "./api";
import { sidecarFetch } from "./sidecarFetch";

export type SidecarEventType =
  | "generation.updated"
  | "credits.updated"
  | "session.usage";

export interface GenerationUpdatedPayload extends GenerationRecord {}

export interface CreditsUpdatedPayload {
  credits?: number;
  credits_consumed?: number;
}

export interface SessionUsagePayload {
  spent: number;
  limit: number | null;
}

export type SidecarEventHandler = {
  onGenerationUpdated?: (data: GenerationUpdatedPayload) => void;
  onCreditsUpdated?: (data: CreditsUpdatedPayload) => void;
  onSessionUsage?: (data: SessionUsagePayload) => void;
  onDisconnect?: () => void;
  onConnect?: () => void;
};

type SidecarEventHandlers = SidecarEventHandler;

const MAX_RECONNECT_FAILURES = 3;
const BASE_RECONNECT_MS = 1000;

let sseDegraded = false;
let reconnectFailures = 0;

export function isSseDegraded(): boolean {
  return sseDegraded;
}

function parseSseChunk(
  part: string,
): { eventType: string; dataStr: string } | null {
  if (!part.trim() || part.trim().startsWith(":")) return null;
  let eventType = "message";
  let dataStr = "";
  for (const line of part.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataStr = line.slice(5).trim();
    }
  }
  if (!dataStr) return null;
  return { eventType, dataStr };
}

function dispatchEvent(eventType: string, data: unknown, handlers: SidecarEventHandlers) {
  switch (eventType) {
    case "generation.updated":
      handlers.onGenerationUpdated?.(data as GenerationUpdatedPayload);
      break;
    case "credits.updated":
      handlers.onCreditsUpdated?.(data as CreditsUpdatedPayload);
      break;
    case "session.usage":
      handlers.onSessionUsage?.(data as SessionUsagePayload);
      break;
    default:
      break;
  }
}

export function connectSidecarEvents(
  baseUrl: string,
  handlers: SidecarEventHandlers,
  signal?: AbortSignal,
): void {
  let buffer = "";
  let cancelled = false;

  const run = async () => {
    while (!cancelled && !signal?.aborted) {
      try {
        const response = await sidecarFetch(`${baseUrl}/api/v1/events`, {
          signal,
          headers: { Accept: "text/event-stream" },
        });
        if (!response.ok || !response.body) {
          throw new Error(`SSE failed: ${response.status}`);
        }

        sseDegraded = false;
        reconnectFailures = 0;
        handlers.onConnect?.();

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (!cancelled && !signal?.aborted) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const parsed = parseSseChunk(part);
            if (!parsed) continue;
            try {
              const data = JSON.parse(parsed.dataStr) as unknown;
              dispatchEvent(parsed.eventType, data, handlers);
            } catch {
              // skip malformed
            }
          }
        }
      } catch {
        if (cancelled || signal?.aborted) break;
        handlers.onDisconnect?.();
        reconnectFailures += 1;
        if (reconnectFailures >= MAX_RECONNECT_FAILURES) {
          sseDegraded = true;
          break;
        }
        const delay = BASE_RECONNECT_MS * reconnectFailures;
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  };

  void run();
}
