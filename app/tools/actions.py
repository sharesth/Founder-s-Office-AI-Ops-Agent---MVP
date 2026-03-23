"""
Action-item extraction from meeting notes and transcripts.

Uses a combination of regex-based heuristics (deterministic) for
well-formatted notes and provides a hook for LLM-based extraction
as a fallback.
"""

from __future__ import annotations

import re
import uuid
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import MeetingNoteRecord, TranscriptRecord
from app.schemas import ActionItem, ActionPriority, ActionStatus, Evidence

logger = logging.getLogger(__name__)

# ── Regex patterns for common action-item formats ──────────

_ACTION_PATTERNS = [
    # "- [ ] Do something @owner by 2025-03-20"
    re.compile(
        r"[-*]\s*\[[ ]\]\s*(?P<desc>.+?)(?:\s*@(?P<owner>\w+))?(?:\s+by\s+(?P<due>\S+))?\s*$",
        re.M | re.I,
    ),
    # "ACTION: Do something (Owner: John)"
    re.compile(
        r"(?:ACTION|TODO|TASK|FOLLOW[- ]?UP)\s*:\s*(?P<desc>.+?)(?:\s*\((?:owner|assigned):\s*(?P<owner>[^)]+)\))?(?:\s+by\s+(?P<due>\S+))?\s*$",
        re.M | re.I,
    ),
    # "→ Send proposal to client"
    re.compile(
        r"[→➤►•]\s*(?P<desc>.+?)(?:\s*[-–]\s*(?P<owner>\w+))?\s*$",
        re.M,
    ),
]

_PRIORITY_KEYWORDS = {
    ActionPriority.URGENT: ["urgent", "asap", "immediately", "critical", "blocker"],
    ActionPriority.HIGH: ["high priority", "important", "escalate", "must"],
    ActionPriority.MEDIUM: ["should", "plan", "schedule"],
}


def _detect_priority(text: str) -> ActionPriority:
    lower = text.lower()
    for priority, keywords in _PRIORITY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return priority
    return ActionPriority.MEDIUM


def _parse_due(raw: str | None) -> Optional[date]:
    if not raw:
        return None
    from app.ingest.normalizer import normalize_date
    return normalize_date(raw)


def extract_actions_from_text(
    text: str,
    account_name: str,
    source_file: str,
) -> list[ActionItem]:
    """Extract action items from free-form text using regex heuristics."""
    actions: list[ActionItem] = []
    seen_descs: set[str] = set()

    for pattern in _ACTION_PATTERNS:
        for match in pattern.finditer(text):
            desc = match.group("desc").strip()
            if not desc or desc.lower() in seen_descs:
                continue
            seen_descs.add(desc.lower())

            owner = None
            try:
                owner = match.group("owner")
                if owner:
                    owner = owner.strip()
            except IndexError:
                pass

            due_raw = None
            try:
                due_raw = match.group("due")
            except IndexError:
                pass

            # Build surrounding context as evidence
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            snippet = text[start:end].strip()

            actions.append(ActionItem(
                action_id=f"ACT-{uuid.uuid4().hex[:8]}",
                account_name=account_name,
                description=desc,
                owner=owner,
                due_date=_parse_due(due_raw),
                priority=_detect_priority(desc),
                status=ActionStatus.PENDING,
                source=source_file,
                evidence=[Evidence(
                    source=source_file,
                    snippet=snippet,
                    relevance="Text surrounding the detected action item",
                )],
            ))

    return actions


def extract_all_action_items(db: Session) -> list[ActionItem]:
    """Scan all meeting notes and transcripts in the DB for action items."""
    all_items: list[ActionItem] = []

    # From meeting notes
    notes = db.query(MeetingNoteRecord).all()
    for note in notes:
        items = extract_actions_from_text(
            text=note.content,
            account_name=note.account_name,
            source_file=note.source_file,
        )
        all_items.extend(items)

    # From transcripts
    transcripts = db.query(TranscriptRecord).all()
    for t in transcripts:
        items = extract_actions_from_text(
            text=t.full_text,
            account_name=t.account_name,
            source_file=t.source_file,
        )
        all_items.extend(items)

    logger.info("Extracted %d action items total", len(all_items))
    return all_items
