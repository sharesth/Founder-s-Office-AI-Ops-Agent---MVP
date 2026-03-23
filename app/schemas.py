"""
Pydantic v2 schemas for the Founder's Office AI Ops Agent.
Covers CRM deals, contacts, meeting notes, transcripts, and all
analysis output types: Blockers, ChurnRisks, ActionItems, FollowUps, Reports.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ──────────────────────────────────────────────────

class DealStage(str, Enum):
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class OnboardingStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DELAYED = "delayed"
    COMPLETED = "completed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


# ── CRM Input Schemas ─────────────────────────────────────

class DealRecord(BaseModel):
    """Raw CRM deal after CSV ingestion."""
    deal_id: str = Field(..., description="Unique deal identifier")
    account_name: str = Field(..., description="Normalized company name")
    contact_name: str = Field(..., description="Primary contact")
    contact_email: Optional[str] = None
    deal_value: float = Field(ge=0, description="Deal value in USD")
    stage: DealStage
    next_step: Optional[str] = Field(None, description="Planned next action")
    last_activity_date: Optional[date] = Field(None, description="Most recent activity")
    expected_close_date: Optional[date] = None
    owner: str = Field(..., description="Sales rep")
    created_at: Optional[datetime] = None
    notes: Optional[str] = None

    # ── Business-rule helpers ──────────────────────────────
    renewal_days_left: Optional[int] = Field(None, description="Days until renewal")
    ticket_count: Optional[int] = Field(0, description="Open support tickets")
    onboarding_status: Optional[OnboardingStatus] = None

    @field_validator("account_name", mode="before")
    @classmethod
    def normalize_account(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("contact_name", mode="before")
    @classmethod
    def normalize_contact(cls, v: str) -> str:
        return v.strip()


class MeetingNote(BaseModel):
    """Parsed meeting note or call note."""
    note_id: str
    account_name: str
    date: date
    attendees: list[str] = Field(default_factory=list)
    content: str
    source_file: str

    @field_validator("account_name", mode="before")
    @classmethod
    def normalize_account(cls, v: str) -> str:
        return v.strip().lower()


class TranscriptMessage(BaseModel):
    """Single utterance inside a call transcript."""
    speaker: str
    timestamp: Optional[str] = None
    text: str


class CallTranscript(BaseModel):
    """Parsed call transcript."""
    transcript_id: str
    account_name: str
    date: date
    messages: list[TranscriptMessage] = Field(default_factory=list)
    source_file: str

    @field_validator("account_name", mode="before")
    @classmethod
    def normalize_account(cls, v: str) -> str:
        return v.strip().lower()


# ── Analysis Output Schemas ────────────────────────────────

class Evidence(BaseModel):
    """A snippet of source text that backs an insight."""
    source: str = Field(..., description="File or record the snippet came from")
    snippet: str = Field(..., description="Verbatim excerpt")
    relevance: Optional[str] = Field(None, description="Why this evidence matters")


class Blocker(BaseModel):
    """A pipeline blocker detected by deterministic rules or LLM."""
    blocker_id: str
    deal_id: str
    account_name: str
    rule_triggered: str = Field(..., description="e.g. 'stalled_deal', 'missing_next_step'")
    description: str
    days_inactive: Optional[int] = None
    stage: Optional[DealStage] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    evidence: list[Evidence] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class ChurnRisk(BaseModel):
    """A churn-risk flag for an existing customer."""
    risk_id: str
    account_name: str
    deal_id: Optional[str] = None
    risk_level: RiskLevel
    reasons: list[str] = Field(..., description="Plain-English reasons")
    renewal_days_left: Optional[int] = None
    ticket_count: Optional[int] = None
    onboarding_status: Optional[OnboardingStatus] = None
    evidence: list[Evidence] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class ActionItem(BaseModel):
    """An action extracted from meeting notes or transcripts."""
    action_id: str
    account_name: str
    description: str
    owner: Optional[str] = None
    due_date: Optional[date] = None
    priority: ActionPriority = ActionPriority.MEDIUM
    status: ActionStatus = ActionStatus.PENDING
    source: str = Field(..., description="Source file or transcript")
    evidence: list[Evidence] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FollowUpEmail(BaseModel):
    """An LLM-drafted follow-up email."""
    email_id: str
    account_name: str
    to: str
    subject: str
    body: str
    tone: str = Field(default="professional", description="e.g. professional, urgent, warm")
    evidence: list[Evidence] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineSummary(BaseModel):
    """Aggregate pipeline KPIs."""
    total_deals: int
    total_pipeline_value: float
    deals_by_stage: dict[str, int]
    avg_deal_value: float
    stalled_count: int
    closing_without_next_step: int


class WeeklyReport(BaseModel):
    """Aggregated weekly operations report."""
    report_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    period_start: date
    period_end: date
    pipeline_summary: PipelineSummary
    blockers: list[Blocker] = Field(default_factory=list)
    churn_risks: list[ChurnRisk] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


# ── API Request / Response wrappers ────────────────────────

class IngestRequest(BaseModel):
    """Payload accepted by the /ingest endpoint."""
    file_type: str = Field(..., description="csv | md | txt | json")
    file_name: str


class IngestResponse(BaseModel):
    status: str = "ok"
    records_processed: int = 0
    message: str = ""


class AskRequest(BaseModel):
    """Natural-language question sent to the agent."""
    question: str


class AskResponse(BaseModel):
    answer: str
    evidence: list[Evidence] = Field(default_factory=list)
