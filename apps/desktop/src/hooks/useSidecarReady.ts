import { useCallback, useEffect, useState } from "react";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { getSidecarUrl } from "../lib/sidecar";
import { sidecarFetch } from "../lib/sidecarFetch";

const POLL_MS = 500;
const TIMEOUT_MS = 120_000;

export function useSidecarReady() {
  const [ready, setReady] = useState(false);
  const [timedOut, setTimedOut] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      const deadline = Date.now() + TIMEOUT_MS;
      while (!cancelled && Date.now() < deadline) {
        try {
          if (isTauri()) {
            const ok = await invoke<boolean>("check_sidecar_health", {
              sidecarUrl: null,
            });
            if (ok) {
              if (!cancelled) {
                setReady(true);
                setTimedOut(false);
                setRetrying(false);
              }
              return;
            }
          } else {
            const base = await getSidecarUrl();
            const response = await sidecarFetch(`${base}/health`, {
              signal: AbortSignal.timeout(3_000),
            });
            if (response.ok) {
              if (!cancelled) {
                setReady(true);
                setTimedOut(false);
                setRetrying(false);
              }
              return;
            }
          }
        } catch {
          // sidecar still starting
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_MS));
      }
      if (!cancelled) {
        setTimedOut(true);
        setRetrying(false);
      }
    };

    void poll();
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = useCallback(async () => {
    setRetrying(true);
    setTimedOut(false);
    setReady(false);
    try {
      const sidecarUrl = await getSidecarUrl();
      await invoke("restart_sidecar", { sidecarUrl });
    } catch {
      // still try polling
    }
    setAttempt((n) => n + 1);
  }, []);

  return {
    ready,
    starting: !ready && !timedOut && !retrying,
    timedOut,
    retrying,
    retry,
  };
}
