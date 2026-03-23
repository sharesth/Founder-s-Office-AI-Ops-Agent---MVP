"""
Churn-risk watchlist – deterministic business rules.

Rule:
  Churn Risk flag when:
    renewal_days_left < 60  AND  (ticket_count > 5  OR  onboarding_status == 'delayed')
"""

from __future__ import annotations

import uuid
import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Deal
from app.schemas import (
    ChurnRisk,
    Evidence,
    OnboardingStatus,
    RiskLevel,
)

logger = logging.getLogger(__name__)

RENEWAL_THRESHOLD_DAYS = 60
TICKET_THRESHOLD = 5


def get_churn_watchlist(db: Session) -> list[ChurnRisk]:
    """
    Scan all deals and flag accounts matching churn-risk criteria.
    Every risk is backed by evidence from the CRM record.
    """
    deals = db.query(Deal).all()
    risks: list[ChurnRisk] = []

    for d in deals:
        reasons: list[str] = []

        renewal_days = d.renewal_days_left
        tickets = d.ticket_count or 0
        onboarding = d.onboarding_status

        # Skip if renewal info is missing
        if renewal_days is None:
            continue

        if renewal_days >= RENEWAL_THRESHOLD_DAYS:
            continue  # not approaching renewal

        # At least one secondary signal must fire
        ticket_flag = tickets > TICKET_THRESHOLD
        onboarding_flag = onboarding == OnboardingStatus.DELAYED.value

        if not (ticket_flag or onboarding_flag):
            continue

        # Build reasons
        reasons.append(f"Renewal in {renewal_days} days (< {RENEWAL_THRESHOLD_DAYS}-day threshold)")
        if ticket_flag:
            reasons.append(f"High support ticket count: {tickets} (> {TICKET_THRESHOLD})")
        if onboarding_flag:
            reasons.append("Onboarding status is 'delayed'")

        # Risk level
        risk_level = RiskLevel.HIGH
        if renewal_days < 30:
            risk_level = RiskLevel.CRITICAL
        elif renewal_days < 45 and ticket_flag and onboarding_flag:
            risk_level = RiskLevel.CRITICAL

        evidence = [
            Evidence(
                source=f"CRM deal {d.deal_id}",
                snippet=(
                    f"Account={d.account_name}, Renewal={renewal_days}d, "
                    f"Tickets={tickets}, Onboarding={onboarding}"
                ),
                relevance="CRM fields that triggered the churn-risk rule",
            ),
        ]
        if d.notes:
            evidence.append(Evidence(
                source=f"CRM deal {d.deal_id} notes",
                snippet=d.notes[:300],
                relevance="Context from deal notes",
            ))

        risks.append(ChurnRisk(
            risk_id=f"CHR-{uuid.uuid4().hex[:8]}",
            account_name=d.account_name,
            deal_id=d.deal_id,
            risk_level=risk_level,
            reasons=reasons,
            renewal_days_left=renewal_days,
            ticket_count=tickets,
            onboarding_status=OnboardingStatus(onboarding) if onboarding in [s.value for s in OnboardingStatus] else None,
            evidence=evidence,
            recommended_action=_recommend(d, reasons),
        ))

    logger.info("Found %d churn risks", len(risks))
    return risks


def _recommend(deal: Deal, reasons: list[str]) -> str:
    parts = [f"Schedule an executive check-in with {deal.account_name}."]
    if any("ticket" in r.lower() for r in reasons):
        parts.append("Escalate open support tickets and assign a dedicated CSM.")
    if any("onboarding" in r.lower() for r in reasons):
        parts.append("Fast-track onboarding with a dedicated implementation sprint.")
    return " ".join(parts)
