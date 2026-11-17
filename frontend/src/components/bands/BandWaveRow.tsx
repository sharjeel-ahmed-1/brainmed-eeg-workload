import { useMemo } from "react";
import type { BandInfo } from "../../data/types";
import { useWavePhase } from "../../hooks/useWavePhase";
import "./bands.css";

/** Stable per-band phase offset so rows don't animate in lockstep. */
const BAND_PHASE: Record<string, number> = {
  gamma: 0.0,
  beta: 1.1,
  alpha: 2.3,
  theta: 3.4,
  delta: 4.6,
};

export function BandWaveRow({ band, color }: { band: BandInfo; color: string }) {
  const t = useWavePhase(true, 100);
  const phase0 = BAND_PHASE[band.id] ?? 0;

  // Same smooth sine style as Concentration — no raw series scroll (that wobbles)
  const d = useMemo(() => {
    const w = 220;
    const mid = 16;
    const amp = 5 + band.relative_power * 9;
    const freq = 0.42 + band.relative_power * 0.2;
    return Array.from({ length: 48 }, (_, i) => {
      const x = (i / 47) * w;
      const y =
        mid +
        Math.sin(i * freq + t * 0.7 + phase0 + band.hz_proxy * 0.02) * amp +
        Math.sin(i * 0.95 - t * 0.5 + phase0) * 2.2;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
  }, [t, band.relative_power, band.hz_proxy, phase0]);

  return (
    <div className="band-row">
      <div className="band-row-label">
        <strong>{band.name.toUpperCase()}</strong>
        <span className="muted">{band.label}</span>
      </div>
      <svg className="band-wave" viewBox="0 0 220 32" width="100%" height={32}>
        <path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <div className="band-hz">
        <span>{band.hz_proxy.toFixed(1)} Hz</span>
        <small className="muted">proxy</small>
      </div>
    </div>
  );
}
