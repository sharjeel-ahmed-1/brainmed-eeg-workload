import { useMemo } from "react";
import type { BandInfo } from "../../data/types";
import { useWavePhase } from "../../hooks/useWavePhase";
import "./widgets.css";

export function ConcentrationWidget({
  gamma,
  recorded,
}: {
  gamma?: BandInfo;
  recorded: boolean;
}) {
  const hz = gamma?.hz_proxy ?? 0;
  const range = gamma?.range_hz ?? [30, 40];
  const t = useWavePhase(true, 100);
  const wave = useMemo(() => {
    const amp = 7 + (gamma?.relative_power ?? 0.2) * 10;
    return Array.from({ length: 48 }, (_, i) => {
      const x = (i / 47) * 200;
      const y =
        20 +
        Math.sin(i * 0.55 + t * 0.7 + hz * 0.03) * amp +
        Math.sin(i * 1.1 - t * 0.5) * 2.5;
      return `${i === 0 ? "M" : "L"}${x},${y}`;
    }).join(" ");
  }, [t, hz, gamma?.relative_power]);
  return (
    <aside className="float-card glass concentration-card">
      <div className="float-head">
        <span>Concentration</span>
        {recorded ? (
          <span className="live-dot" title="Scored from recording">
            <i /> Recorded
          </span>
        ) : (
          <span className="demo-pill">DEMO</span>
        )}
      </div>
      <div className="conc-row">
        <span className="conc-symbol">γ</span>
        <div>
          <div className="conc-hz">{hz.toFixed(1)} Hz</div>
          <div className="muted tiny">
            Range {range[0]}–{range[1]} Hz
          </div>
        </div>
      </div>
      <svg viewBox="0 0 200 40" width="100%" height="40" className="conc-wave">
        <path d={wave} fill="none" stroke="#7ec8ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="acq">
        {recorded ? "Acquisition: offline recording score" : "DEMO acquisition"}
      </div>
    </aside>
  );
}
