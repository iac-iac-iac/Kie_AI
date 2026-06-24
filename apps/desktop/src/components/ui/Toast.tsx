import { useEffect, useState } from "react";
import { subscribeToast } from "../../lib/toast";

export function Toast() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    return subscribeToast((text) => {
      setMessage(text);
      window.setTimeout(() => setMessage(null), 5000);
    });
  }, []);

  if (!message) return null;

  return (
    <div className="pointer-events-none fixed bottom-20 left-1/2 z-50 max-w-md -translate-x-1/2 rounded-xl border border-[var(--glass-border)] bg-[var(--glass-bg)] px-4 py-3 text-sm text-primary shadow-lg backdrop-blur-xl">
      {message}
    </div>
  );
}
