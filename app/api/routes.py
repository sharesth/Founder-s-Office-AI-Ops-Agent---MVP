"""
FastAPI routes for the Founder's Office AI Ops Agent.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models import get_db, init_db
from app.ingest.csv_parser import parse_csv, persist_deals
from app.ingest.text_parser import (
    parse_meeting_note,
    parse_transcript_json,
    parse_transcript_txt,
    persist_meeting_notes,
    persist_transcripts,
)
from app.retrieval.hybrid import build_index
from app.tools.pipeline import get_pipeline_summary, get_stalled_deals
from app.tools.churn import get_churn_watchlist
from app.tools.actions import extract_all_action_items
from app.agents.orchestrator import ask_question, draft_email
from app.schemas import (
    AskRequest,
    AskResponse,
    IngestResponse,
    PipelineSummary,
)

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ── Health ─────────────────────────────────────────────────

@router.get("/health")
def health():
    return {"status": "ok"}


# ── Ingest ─────────────────────────────────────────────────

@router.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and ingest a CRM CSV, meeting note, or transcript."""
    suffix = Path(file.filename).suffix.lower()

    # Save to disk
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        if suffix == ".csv":
            records = parse_csv(dest)
            count = persist_deals(records, db)
            return IngestResponse(records_processed=count, message=f"Ingested {count} deals")

        if suffix in (".md", ".txt"):
            # attempt transcript-style parse; fall back to meeting note
            try:
                note = parse_meeting_note(dest)
                count = persist_meeting_notes([note], db)
                return IngestResponse(records_processed=count, message=f"Ingested meeting note: {file.filename}")
            except Exception:
                pass

        if suffix == ".json":
            transcript = parse_transcript_json(dest)
            count = persist_transcripts([transcript], db)
            return IngestResponse(records_processed=count, message=f"Ingested transcript: {file.filename}")

        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ingest/build-index")
def ingest_build_index(db: Session = Depends(get_db)):
    """(Re-)build the FAISS vector index from all ingested documents."""
    count = build_index(db)
    return {"status": "ok", "documents_indexed": count}


# ── Pipeline ───────────────────────────────────────────────

@router.get("/pipeline/summary", response_model=PipelineSummary)
def pipeline_summary(db: Session = Depends(get_db)):
    return get_pipeline_summary(db)


@router.get("/pipeline/blockers")
def pipeline_blockers(db: Session = Depends(get_db)):
    blockers = get_stalled_deals(db)
    return [b.model_dump() for b in blockers]


# ── Churn ──────────────────────────────────────────────────

@router.get("/churn/watchlist")
def churn_watchlist(db: Session = Depends(get_db)):
    risks = get_churn_watchlist(db)
    return [r.model_dump() for r in risks]


# ── Actions ────────────────────────────────────────────────

@router.get("/actions")
def action_items(db: Session = Depends(get_db)):
    items = extract_all_action_items(db)
    return [i.model_dump() for i in items]


# ── Ask ────────────────────────────────────────────────────

@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, db: Session = Depends(get_db)):
    return ask_question(req.question, db)


# ── Email Drafter ──────────────────────────────────────────

@router.post("/email/draft")
def email_draft(
    account_name: str,
    to: str,
    purpose: str,
    tone: str = "professional",
    db: Session = Depends(get_db),
):
    email = draft_email(account_name, to, purpose, db, tone=tone)
    return email.model_dump()
