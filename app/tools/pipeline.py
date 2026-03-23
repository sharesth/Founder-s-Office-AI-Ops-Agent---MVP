"""
Pipeline analysis tools – deterministic business rules.

Rules implemented:
  1. Stalled Deal: No activity for > 14 days OR next_step is null.
  2. Missing Data: Deal in 'Closing' stage without a next_step.
"""

from __future__ import annotations

import uuid
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Deal
from app.schemas import (
    Blocker,
    DealStage,
    Evidence,
    PipelineSummary,
    RiskLevel,
)

logger = logging.getLogger(__name__)

STALLED_THRESHOLD_DAYS = 14


def get_pipeline_summary(db: Session) -> PipelineSummary:
    """
    Compute aggregate KPIs across all deals in the database.
    Pure SQL aggregation – no LLM needed.
    """
    deals = db.query(Deal).all()

    if not deals:
        return PipelineSummary(
            total_deals=0,
            total_pipeline_value=0.0,
            deals_by_stage={},
            avg_deal_value=0.0,
            stalled_count=0,
            closing_without_next_step=0,
        )

    total_value = sum(d.deal_value for d in deals)
    stage_counts: dict[str, int] = {}
    stalled = 0
    closing_no_step = 0
    today = date.today()

    for d in deals:
        stage_counts[d.stage] = stage_counts.get(d.stage, 0) + 1

        # stalled check
        if _is_stalled(d, today):
            stalled += 1

        # closing without next step
        if d.stage == DealStage.CLOSING.value and not d.next_step:
            closing_no_step += 1

    return PipelineSummary(
        total_deals=len(deals),
        total_pipeline_value=total_value,
        deals_by_stage=stage_counts,
        avg_deal_value=round(total_value / len(deals), 2) if deals else 0,
        stalled_count=stalled,
        closing_without_next_step=closing_no_step,
    )


def get_stalled_deals(db: Session) -> list[Blocker]:
    """
    Return Blocker records for every deal that triggers the stalled-deal
    or missing-next-step rules.
    """
    deals = db.query(Deal).all()
    today = date.today()
    blockers: list[Blocker] = []

    for d in deals:
        reasons: list[str] = []
        days_inactive: Optional[int] = None

        # Rule 1 – no activity for > 14 days
        if d.last_activity_date:
            delta = (today - d.last_activity_date).days
            if delta > STALLED_THRESHOLD_DAYS:
                days_inactive = delta
                reasons.append(f"No activity for {delta} days (threshold: {STALLED_THRESHOLD_DAYS})")

        # Rule 1b – next_step is null (also counts as stalled)
        if not d.next_step:
            reasons.append("Next step is empty/null")

        # Rule 2 – Closing stage without next step
        if d.stage == DealStage.CLOSING.value and not d.next_step:
            reasons.append("Deal in 'Closing' stage with no defined next step — high risk")

        if not reasons:
            continue

        # Determine risk level
        risk = RiskLevel.MEDIUM
        if d.stage == DealStage.CLOSING.value and not d.next_step:
            risk = RiskLevel.CRITICAL
        elif days_inactive and days_inactive > 30:
            risk = RiskLevel.HIGH

        evidence_items = []
        if d.notes:
            evidence_items.append(Evidence(
                source=f"CRM deal {d.deal_id}",
                snippet=d.notes[:300],
                relevance="Latest CRM notes on this deal",
            ))
        evidence_items.append(Evidence(
            source=f"CRM deal {d.deal_id}",
            snippet=f"Stage={d.stage}, Last Activity={d.last_activity_date}, Next Step={d.next_step}",
            relevance="Deal metadata triggering the rule",
        ))

        blockers.append(Blocker(
            blocker_id=f"BLK-{uuid.uuid4().hex[:8]}",
            deal_id=d.deal_id,
            account_name=d.account_name,
            rule_triggered=", ".join(reasons),
            description=f"Deal '{d.account_name}' flagged: {'; '.join(reasons)}.",
            days_inactive=days_inactive,
            stage=DealStage(d.stage) if d.stage in [s.value for s in DealStage] else None,
            risk_level=risk,
            evidence=evidence_items,
            recommended_action=_recommend_action(d, reasons),
        ))

    logger.info("Found %d pipeline blockers", len(blockers))
    return blockers


# ── Internal helpers ───────────────────────────────────────

def _is_stalled(deal: Deal, today: date) -> bool:
    if not deal.next_step:
        return True
    if deal.last_activity_date:
        return (today - deal.last_activity_date).days > STALLED_THRESHOLD_DAYS
    return False


def _recommend_action(deal: Deal, reasons: list[str]) -> str:
    if deal.stage == DealStage.CLOSING.value and not deal.next_step:
        return (
            f"URGENT: Add a concrete next step for {deal.account_name}. "
            "This deal is in Closing without a defined action — risk of silent drop."
        )
    if any("No activity" in r for r in reasons):
        return (
            f"Re-engage {deal.contact_name} at {deal.account_name}. "
            "Consider sending a value-add email or scheduling a quick check-in call."
        )
    return f"Review deal {deal.deal_id} and define a clear next step."
