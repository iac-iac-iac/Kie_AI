import { useEffect, useState } from "react";
import { getSidecarUrl } from "../lib/sidecar";

const POLL_MS = 500;
const TIMEOUT_MS = 120_000;

export function useSidecarReady() {
  const [ready, setReady] = useState(false);
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      const deadline = Date.now() + TIMEOUT_MS;
      while (!cancelled && Date.now() < deadline) {
        try {
          const base = await getSidecarUrl();
          const response = await fetch(`${base}/health`, {
            signal: AbortSignal.timeout(3_000),
          });
          if (response.ok) {
            if (!cancelled) {
              setReady(true);
              setTimedOut(false);
            }
            return;
          }
        } catch {
          // sidecar still starting (PyInstaller onefile extract on first launch)
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_MS));
      }
      if (!cancelled) {
        setTimedOut(true);
      }
    };

    void poll();
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    ready,
    starting: !ready && !timedOut,
    timedOut,
  };
}
