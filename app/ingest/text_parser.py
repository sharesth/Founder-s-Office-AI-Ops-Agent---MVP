"""
Meeting-note (MD/TXT) and Call-transcript (JSON/TXT) parsers.

Each parser returns the corresponding Pydantic schema and persists to SQLite.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Sequence

from sqlalchemy.orm import Session

from app.db.models import MeetingNoteRecord, TranscriptRecord
from app.ingest.normalizer import normalize_date, normalize_name
from app.schemas import CallTranscript, MeetingNote, TranscriptMessage

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# Meeting Notes  (*.md  /  *.txt)
# ────────────────────────────────────────────────────────────

_ACCOUNT_RE = re.compile(r"(?:account|company|client)\s*:\s*(.+)", re.I)
_DATE_RE = re.compile(r"(?:date)\s*:\s*(.+)", re.I)
_ATTENDEES_RE = re.compile(r"(?:attendees|participants)\s*:\s*(.+)", re.I)


def _extract_front_matter(text: str) -> dict[str, str]:
    """Pull simple `Key: Value` metadata from the top of a note."""
    meta: dict[str, str] = {}
    for line in text.splitlines()[:15]:  # only scan first 15 lines
        m = _ACCOUNT_RE.match(line)
        if m:
            meta["account_name"] = m.group(1).strip()
        m = _DATE_RE.match(line)
        if m:
            meta["date"] = m.group(1).strip()
        m = _ATTENDEES_RE.match(line)
        if m:
            meta["attendees"] = m.group(1).strip()
    return meta


def parse_meeting_note(file_path: str | Path) -> MeetingNote:
    """Parse a single MD/TXT meeting note file."""
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    meta = _extract_front_matter(text)

    note_id = hashlib.md5(text.encode()).hexdigest()[:12]
    account = normalize_name(meta.get("account_name", path.stem))
    note_date = normalize_date(meta.get("date")) or date.today()
    attendees = [a.strip() for a in meta.get("attendees", "").split(",") if a.strip()]

    return MeetingNote(
        note_id=note_id,
        account_name=account,
        date=note_date,
        attendees=attendees,
        content=text,
        source_file=path.name,
    )


def persist_meeting_notes(notes: Sequence[MeetingNote], db: Session) -> int:
    count = 0
    for n in notes:
        exists = db.query(MeetingNoteRecord).filter_by(note_id=n.note_id).first()
        if exists:
            continue
        db.add(MeetingNoteRecord(
            note_id=n.note_id,
            account_name=n.account_name,
            date=n.date,
            attendees=", ".join(n.attendees),
            content=n.content,
            source_file=n.source_file,
        ))
        count += 1
    db.commit()
    return count


# ────────────────────────────────────────────────────────────
# Call Transcripts  (*.json  /  *.txt)
# ────────────────────────────────────────────────────────────

def parse_transcript_json(file_path: str | Path) -> CallTranscript:
    """Parse a JSON call transcript."""
    path = Path(file_path)
    data = json.loads(path.read_text(encoding="utf-8"))

    transcript_id = data.get("transcript_id") or hashlib.md5(path.read_bytes()).hexdigest()[:12]
    account = normalize_name(data.get("account_name", data.get("account", path.stem)))
    t_date = normalize_date(data.get("date")) or date.today()

    messages: list[TranscriptMessage] = []
    for msg in data.get("messages", data.get("transcript", [])):
        messages.append(TranscriptMessage(
            speaker=msg.get("speaker", "unknown"),
            timestamp=msg.get("timestamp"),
            text=msg.get("text", ""),
        ))

    return CallTranscript(
        transcript_id=transcript_id,
        account_name=account,
        date=t_date,
        messages=messages,
        source_file=path.name,
    )


def parse_transcript_txt(file_path: str | Path) -> CallTranscript:
    """Parse a plaintext transcript (Speaker: text format)."""
    path = Path(file_path)
    raw = path.read_text(encoding="utf-8")

    meta = _extract_front_matter(raw)
    transcript_id = hashlib.md5(raw.encode()).hexdigest()[:12]
    account = normalize_name(meta.get("account_name", path.stem))
    t_date = normalize_date(meta.get("date")) or date.today()

    speaker_re = re.compile(r"^([A-Za-z\s]+?):\s*(.+)$", re.M)
    messages = [
        TranscriptMessage(speaker=m.group(1).strip(), text=m.group(2).strip())
        for m in speaker_re.finditer(raw)
    ]

    return CallTranscript(
        transcript_id=transcript_id,
        account_name=account,
        date=t_date,
        messages=messages,
        source_file=path.name,
    )


def persist_transcripts(transcripts: Sequence[CallTranscript], db: Session) -> int:
    count = 0
    for t in transcripts:
        exists = db.query(TranscriptRecord).filter_by(transcript_id=t.transcript_id).first()
        if exists:
            continue
        full_text = "\n".join(f"{m.speaker}: {m.text}" for m in t.messages)
        db.add(TranscriptRecord(
            transcript_id=t.transcript_id,
            account_name=t.account_name,
            date=t.date,
            full_text=full_text,
            source_file=t.source_file,
        ))
        count += 1
    db.commit()
    return count
