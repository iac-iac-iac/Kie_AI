export type StreamEventType = "delta" | "done" | "error";

export interface StreamDeltaPayload {
  text: string;
}

export interface StreamDonePayload {
  tokens_in: number;
  tokens_out: number;
  credits: number;
}

export interface StreamErrorPayload {
  code: number;
  message: string;
}

export type StreamHandler = (event: StreamEventType, data: unknown) => void;

export async function consumeSseStream(
  response: Response,
  onEvent: StreamHandler,
): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      if (!part.trim()) continue;
      let eventType = "message";
      let dataStr = "";

      for (const line of part.split("\n")) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataStr = line.slice(5).trim();
        }
      }

      if (!dataStr) continue;
      try {
        const data = JSON.parse(dataStr) as unknown;
        onEvent(eventType as StreamEventType, data);
      } catch {
        // skip malformed chunks
      }
    }
  }
}
