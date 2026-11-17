import { useEffect, useState } from "react";

/** Shared ticker (~10fps) — visible smooth drift, not frantic. */
export function useWavePhase(enabled = true, intervalMs = 100): number {
  const [t, setT] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = window.setInterval(() => setT((x) => x + 0.09), intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs]);
  return t;
}
