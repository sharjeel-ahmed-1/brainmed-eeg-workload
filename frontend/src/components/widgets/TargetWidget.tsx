import { useEffect, useState } from "react";
import type { DemoDashboard } from "../../data/types";
import "./widgets.css";

const KEY = "brainmed_target_pct";

export function TargetWidget({ demo }: { demo: DemoDashboard }) {
  const [target, setTarget] = useState(() => {
    const raw = localStorage.getItem(KEY);
    return raw ? Number(raw) : demo.target.target_pct;
  });
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(target));

  useEffect(() => {
    localStorage.setItem(KEY, String(target));
  }, [target]);

  const onTarget = Math.min(100, (demo.general.progress_pct / Math.max(target, 1)) * 58.7);

  return (
    <aside className="float-card glass target-card">
      <div className="target-pct">{onTarget.toFixed(1)}%</div>
      <div className="muted">On Target (demo)</div>
      {editing ? (
        <form
          className="target-form"
          onSubmit={(e) => {
            e.preventDefault();
            const v = Math.max(5, Math.min(100, Number(draft) || target));
            setTarget(v);
            setEditing(false);
          }}
        >
          <input
            type="number"
            min={5}
            max={100}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <button type="submit">Save</button>
        </form>
      ) : (
        <button type="button" className="target-btn" onClick={() => setEditing(true)}>
          Set new target
        </button>
      )}
      <div className="muted tiny">Stored target: {target}%</div>
    </aside>
  );
}
