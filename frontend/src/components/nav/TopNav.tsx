import { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import "./TopNav.css";

const links = [
  { to: "/", label: "Overview" },
  { to: "/history", label: "My History" },
  { to: "/reports", label: "Reports" },
];

export function TopNav() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <header className="topnav-wrap">
      <nav className="topnav glass">
        <div className="brand">
          <span className="brand-mark" aria-hidden>
            ◉
          </span>
          <span className="brand-name">
            BrainMed<span className="plus">+</span>
          </span>
        </div>
        <div className="nav-links">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {l.label}
            </NavLink>
          ))}
        </div>
        <div className="profile" ref={ref}>
          <button
            type="button"
            className="profile-btn"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            <span className="avatar" aria-hidden>
              RJ
            </span>
            <span className="profile-name">Richard Jarule</span>
            <span className="caret">▾</span>
          </button>
          {open && (
            <div className="profile-menu glass" role="menu">
              <button type="button" role="menuitem" onClick={() => setOpen(false)}>
                Profile settings (demo)
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  alert("No auth backend — logout is a stub.");
                }}
              >
                Log out
              </button>
            </div>
          )}
        </div>
      </nav>
    </header>
  );
}
