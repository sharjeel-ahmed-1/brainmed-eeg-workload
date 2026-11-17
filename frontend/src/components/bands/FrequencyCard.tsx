import { useMemo } from "react";
import type { BandInfo } from "../../data/types";
import { useWavePhase } from "../../hooks/useWavePhase";
import "./bands.css";

const TIPS: Record<string, string> = {
  gamma: "Often linked with focused attention; here shown from relative γ power.",
  beta: "Associated with active thinking; relative β power drives this card.",
  alpha: "Commonly linked with relaxed alertness; relative α power.",
  delta: "Slow activity; relative δ power (not sleep staging).",
  theta: "Mid-slow band; relative θ power (not clinical sleep scoring).",
};

type Props = {
  band: BandInfo;
  color: string;
  onOpen: (band: BandInfo) => void;
};

export function FrequencyCard({ band, color, onOpen }: Props) {
  const t = useWavePhase(true, 100);

  const path = useMemo(() => {
    const n = 36;
    const pts: string[] = [];
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * 120;
      const y =
        18 +
        Math.sin(i * 0.45 + t * (0.55 + band.relative_power * 0.35)) *
          (6 + band.relative_power * 8) +
        Math.sin(i * 0.9 - t * 0.55) * 3;
      pts.push(`${i === 0 ? "M" : "L"}${x},${y}`);
    }
    return pts.join(" ");
  }, [t, band.relative_power]);

  return (
    <button
      type="button"
      className="freq-card glass"
      onClick={() => onOpen(band)}
      title={TIPS[band.id] ?? "EEG band"}
    >
      <div className="freq-top">
        <span className="freq-title">
          {band.label}
          <span className="freq-info" title={TIPS[band.id] ?? "EEG band"} aria-hidden>
            i
          </span>
        </span>
        <span className="freq-symbol" style={{ color }}>
          {band.symbol}
        </span>
      </div>
      <div className="freq-name">{band.name.toUpperCase()}</div>
      <div className="freq-value" style={{ color }}>
        {band.hz_proxy.toFixed(1)} <small>Hz</small>
      </div>
      <div className="muted freq-range">
        Range: {band.range_hz[0]}–{band.range_hz[1]} Hz
      </div>
      <svg viewBox="0 0 120 36" className="freq-mini">
        <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}

export function FrequencyModal({
  band,
  color,
  onClose,
}: {
  band: BandInfo;
  color: string;
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal onClick={onClose}>
      <div className="modal glass" onClick={(e) => e.stopPropagation()}>
        <header>
          <h3>
            {band.label} · {band.name.toUpperCase()} {band.symbol}
          </h3>
          <button type="button" onClick={onClose}>
            Close
          </button>
        </header>
        <p className="muted">{TIPS[band.id]}</p>
        <p>
          Relative power: <strong>{(band.relative_power * 100).toFixed(1)}%</strong> · Display Hz
          proxy: <strong>{band.hz_proxy.toFixed(2)}</strong>
        </p>
        <p className="muted">{band.hz_note}</p>
        <svg viewBox="0 0 320 80" width="100%" height={80}>
          <path
            d={band.series
              .slice(0, 80)
              .map((v, i, arr) => {
                const max = Math.max(...arr, 1e-6);
                const y = 70 - (v / max) * 60;
                const x = (i / Math.max(arr.length - 1, 1)) * 320;
                return `${i === 0 ? "M" : "L"}${x},${y}`;
              })
              .join(" ")}
            fill="none"
            stroke={color}
            strokeWidth="2.5"
          />
        </svg>
      </div>
    </div>
  );
}
