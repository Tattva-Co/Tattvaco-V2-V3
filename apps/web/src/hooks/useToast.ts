import { useEffect, useState } from "react";

/** Mirrors the wireframe's `toast()` helper: a single transient bottom-right message,
 * auto-dismissed. One message at a time is enough for V1 -- a new call replaces
 * whatever is showing rather than queuing. */
export function useToast() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!message) return undefined;
    const timer = window.setTimeout(() => setMessage(null), 4000);
    return () => window.clearTimeout(timer);
  }, [message]);

  return { message, showToast: setMessage };
}
