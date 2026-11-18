"""
Lightweight free DB for BrainMed+ session history.

- Default: SQLite file at data/app.db (local / ephemeral on some hosts)
- Production: set DATABASE_URL to free Postgres (Neon / Render / etc.)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

import config

_raw_url = (os.environ.get("DATABASE_URL") or "").strip()
if _raw_url.startswith("postgres://"):
    # SQLAlchemy + psycopg3
    DATABASE_URL = _raw_url.replace("postgres://", "postgresql+psycopg://", 1)
elif _raw_url.startswith("postgresql://") and "+psycopg" not in _raw_url:
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif _raw_url:
    DATABASE_URL = _raw_url
else:
    db_path = config.ROOT / "data" / "app.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{db_path}"

DB_BACKEND = "postgres" if DATABASE_URL.startswith("postgresql") else "sqlite"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DB_BACKEND == "sqlite" else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class HistoryRow(Base):
    __tablename__ = "history_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_key: Mapped[str] = mapped_column(String(64), index=True)
    # ISO-8601 string (avoids SQLite timezone quirks; works on Postgres too)
    at: Mapped[str] = mapped_column(String(64), index=True)
    label: Mapped[str] = mapped_column(String(512))
    pred_label: Mapped[str] = mapped_column(String(32))
    p_high: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(128))
    subject_idx: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def db_info() -> Dict[str, Any]:
    return {"backend": DB_BACKEND, "configured": True}


def _normalize_at(value: str) -> str:
    raw = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def add_history(
    *,
    client_key: str,
    entry_id: str,
    at: str,
    label: str,
    pred_label: str,
    p_high: float,
    source: str,
    subject_idx: Optional[int] = None,
    model_type: Optional[str] = None,
    display_name: Optional[str] = None,
) -> Dict[str, Any]:
    with SessionLocal() as session:
        row = session.get(HistoryRow, entry_id)
        if row is None:
            row = HistoryRow(id=entry_id, client_key=client_key)
            session.add(row)
        row.client_key = client_key
        row.at = _normalize_at(at)
        row.label = label[:512]
        row.pred_label = pred_label[:32]
        row.p_high = float(p_high)
        row.source = source[:128]
        row.subject_idx = subject_idx
        row.model_type = (model_type or None)
        row.display_name = (display_name or None)
        session.commit()
        return _row_dict(row)


def list_history(client_key: str, limit: int = 40) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(HistoryRow)
            .where(HistoryRow.client_key == client_key)
            .order_by(HistoryRow.at.desc())
            .limit(limit)
        ).all()
        return [_row_dict(r) for r in rows]


def clear_history(client_key: str) -> int:
    with SessionLocal() as session:
        rows = session.scalars(
            select(HistoryRow).where(HistoryRow.client_key == client_key)
        ).all()
        n = len(rows)
        for r in rows:
            session.delete(r)
        session.commit()
        return n


def _row_dict(row: HistoryRow) -> Dict[str, Any]:
    return {
        "id": row.id,
        "at": row.at,
        "label": row.label,
        "pred_label": row.pred_label,
        "p_high": float(row.p_high),
        "source": row.source,
        "subject_idx": row.subject_idx,
        "model_type": row.model_type,
        "display_name": row.display_name,
    }
