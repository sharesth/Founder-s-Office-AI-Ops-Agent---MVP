"""
Normalisation helpers shared across all ingest parsers.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from dateutil import parser as dateutil_parser


def normalize_name(raw: str) -> str:
    """Lowercase, strip whitespace, collapse internal whitespace."""
    return re.sub(r"\s+", " ", raw.strip().lower())


def normalize_date(raw: str | date | datetime | None) -> Optional[date]:
    """Best-effort parse of any date-like string into a `date` object."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    raw_str = str(raw).strip()
    if not raw_str:
        return None
    try:
        return dateutil_parser.parse(raw_str).date()
    except (ValueError, OverflowError):
        return None


def normalize_email(raw: str | None) -> Optional[str]:
    if not raw:
        return None
    return raw.strip().lower()


def safe_float(raw, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def safe_int(raw, default: int = 0) -> int:
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default
