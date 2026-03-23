"""
CSV → DealRecord parser.

Reads a CRM-style CSV, normalises every row, and upserts into the SQLite `deals` table.
"""

from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path
from typing import Sequence

import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Deal
from app.ingest.normalizer import (
    normalize_date,
    normalize_email,
    normalize_name,
    safe_float,
    safe_int,
)
from app.schemas import DealRecord, DealStage, OnboardingStatus

logger = logging.getLogger(__name__)

# Expected CSV columns → internal field mapping
_COLUMN_MAP: dict[str, str] = {
    "deal_id": "deal_id",
    "account_name": "account_name",
    "account": "account_name",
    "company": "account_name",
    "contact_name": "contact_name",
    "contact": "contact_name",
    "contact_email": "contact_email",
    "email": "contact_email",
    "deal_value": "deal_value",
    "value": "deal_value",
    "amount": "deal_value",
    "stage": "stage",
    "deal_stage": "stage",
    "next_step": "next_step",
    "next step": "next_step",
    "last_activity_date": "last_activity_date",
    "last_activity": "last_activity_date",
    "expected_close_date": "expected_close_date",
    "close_date": "expected_close_date",
    "owner": "owner",
    "rep": "owner",
    "sales_rep": "owner",
    "notes": "notes",
    "renewal_days_left": "renewal_days_left",
    "renewal_days": "renewal_days_left",
    "ticket_count": "ticket_count",
    "tickets": "ticket_count",
    "onboarding_status": "onboarding_status",
    "onboarding": "onboarding_status",
    "created_at": "created_at",
}


def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns using the canonical mapping (case-insensitive)."""
    rename: dict[str, str] = {}
    for col in df.columns:
        key = col.strip().lower().replace(" ", "_")
        if key in _COLUMN_MAP:
            rename[col] = _COLUMN_MAP[key]
    return df.rename(columns=rename)


def _coerce_stage(raw: str | None) -> DealStage:
    if not raw:
        return DealStage.PROSPECTING
    cleaned = raw.strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return DealStage(cleaned)
    except ValueError:
        # fuzzy fallback
        for member in DealStage:
            if member.value in cleaned or cleaned in member.value:
                return member
        return DealStage.PROSPECTING


def _coerce_onboarding(raw: str | None) -> OnboardingStatus | None:
    if not raw:
        return None
    cleaned = raw.strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return OnboardingStatus(cleaned)
    except ValueError:
        return None


def parse_csv(file_path: str | Path) -> list[DealRecord]:
    """Read a CSV file and return validated DealRecord objects."""
    path = Path(file_path)
    df = pd.read_csv(
        path,
        dtype=str,
        quotechar='"',
        on_bad_lines="warn",
        engine="python",
    ).fillna("")
    df = _map_columns(df)

    records: list[DealRecord] = []
    for idx, row in df.iterrows():
        try:
            deal_id = row.get("deal_id", "").strip()
            if not deal_id:
                deal_id = hashlib.md5(f"{row.get('account_name', '')}_{idx}".encode()).hexdigest()[:12]

            record = DealRecord(
                deal_id=deal_id,
                account_name=row.get("account_name", "unknown"),
                contact_name=row.get("contact_name", "unknown"),
                contact_email=normalize_email(row.get("contact_email")),
                deal_value=safe_float(row.get("deal_value")),
                stage=_coerce_stage(row.get("stage")),
                next_step=row.get("next_step") or None,
                last_activity_date=normalize_date(row.get("last_activity_date")),
                expected_close_date=normalize_date(row.get("expected_close_date")),
                owner=row.get("owner", "unassigned").strip(),
                notes=row.get("notes") or None,
                renewal_days_left=safe_int(row.get("renewal_days_left")) if row.get("renewal_days_left") else None,
                ticket_count=safe_int(row.get("ticket_count")),
                onboarding_status=_coerce_onboarding(row.get("onboarding_status")),
                created_at=normalize_date(row.get("created_at")),
            )
            records.append(record)
        except Exception as exc:
            logger.warning("Row %d skipped: %s", idx, exc)

    logger.info("Parsed %d deal records from %s", len(records), path.name)
    return records


def persist_deals(records: Sequence[DealRecord], db: Session) -> int:
    """Upsert DealRecords into SQLite. Returns count of rows touched."""
    count = 0
    for rec in records:
        existing = db.query(Deal).filter_by(deal_id=rec.deal_id).first()
        data = {
            "deal_id": rec.deal_id,
            "account_name": rec.account_name,
            "contact_name": rec.contact_name,
            "contact_email": rec.contact_email,
            "deal_value": rec.deal_value,
            "stage": rec.stage.value,
            "next_step": rec.next_step,
            "last_activity_date": rec.last_activity_date,
            "expected_close_date": rec.expected_close_date,
            "owner": rec.owner,
            "notes": rec.notes,
            "renewal_days_left": rec.renewal_days_left,
            "ticket_count": rec.ticket_count,
            "onboarding_status": rec.onboarding_status.value if rec.onboarding_status else None,
        }
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            db.add(Deal(**data))
        count += 1
    db.commit()
    return count
