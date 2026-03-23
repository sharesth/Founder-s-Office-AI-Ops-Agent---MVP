"""
SQLAlchemy models & engine/session factory for the Founder's Office AI Ops Agent.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Date,
    Enum as SAEnum,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# ── Base ───────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── ORM Models ─────────────────────────────────────────────

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deal_id = Column(String(64), unique=True, nullable=False, index=True)
    account_name = Column(String(255), nullable=False, index=True)
    contact_name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=True)
    deal_value = Column(Float, nullable=False, default=0.0)
    stage = Column(String(32), nullable=False)
    next_step = Column(Text, nullable=True)
    last_activity_date = Column(Date, nullable=True)
    expected_close_date = Column(Date, nullable=True)
    owner = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Churn-related fields
    renewal_days_left = Column(Integer, nullable=True)
    ticket_count = Column(Integer, default=0)
    onboarding_status = Column(String(32), nullable=True)


class MeetingNoteRecord(Base):
    __tablename__ = "meeting_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(String(64), unique=True, nullable=False, index=True)
    account_name = Column(String(255), nullable=False, index=True)
    date = Column(Date, nullable=False)
    attendees = Column(Text, nullable=True)   # comma-separated
    content = Column(Text, nullable=False)
    source_file = Column(String(512), nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)


class TranscriptRecord(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_id = Column(String(64), unique=True, nullable=False, index=True)
    account_name = Column(String(255), nullable=False, index=True)
    date = Column(Date, nullable=False)
    full_text = Column(Text, nullable=False)   # flattened messages
    source_file = Column(String(512), nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)


# ── Engine & Session ───────────────────────────────────────

engine = create_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    connect_args={"check_same_thread": False},   # SQLite-specific
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create all tables that don't exist yet."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """FastAPI dependency – yields a session, auto-closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
