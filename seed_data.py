#!/usr/bin/env python3
"""
Seed-data generator for the Founder's Office AI Ops Agent.

Creates:
  • 1 CRM CSV  (20 rows — including 3 stalled deals & 2 churn risks)
  • 5 Meeting notes  (Markdown with action items & objections)
  • 5 Call transcripts  (JSON with "pricing" and "competitor" objections)

Run:  python seed_data.py
"""

from __future__ import annotations

import csv
import json
import os
from datetime import date, timedelta
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent / "data" / "sample"


def _ensure_dirs():
    (SAMPLE_DIR / "meeting_notes").mkdir(parents=True, exist_ok=True)
    (SAMPLE_DIR / "transcripts").mkdir(parents=True, exist_ok=True)


# ── 1. CRM CSV ─────────────────────────────────────────────

def generate_crm_csv():
    today = date.today()

    deals = [
        # Normal deals
        ("D001", "Acme Corp", "Alice Johnson", "alice@acme.com", 45000, "qualification",
         "Schedule demo", today - timedelta(days=3), today + timedelta(days=60), "Sarah Lee",
         "Interested in enterprise plan", "", "2", "in_progress"),
        ("D002", "Beta Inc", "Bob Smith", "bob@beta.com", 120000, "proposal",
         "Send revised proposal", today - timedelta(days=5), today + timedelta(days=30), "Mike Chen",
         "Needs custom integration", "", "1", "completed"),
        ("D003", "CloudFirst", "Carol Davis", "carol@cloudfirst.io", 78000, "negotiation",
         "Legal review pending", today - timedelta(days=2), today + timedelta(days=20), "Sarah Lee",
         "Procurement team involved", "", "0", "completed"),
        ("D004", "DataWave", "Dan Brown", "dan@datawave.com", 35000, "prospecting",
         "Initial call booked", today - timedelta(days=1), today + timedelta(days=90), "Jane Park",
         "Inbound from webinar", "", "0", "not_started"),
        ("D005", "EdgeTech", "Eve Martin", "eve@edgetech.co", 92000, "qualification",
         "Follow up on ROI doc", today - timedelta(days=7), today + timedelta(days=45), "Mike Chen",
         "Comparing us to CompetitorX", "", "1", "not_started"),

        # ★ STALLED DEALS (3) — no activity > 14 days or no next_step
        ("D006", "FutureScale", "Frank Wilson", "frank@futurescale.com", 65000, "proposal",
         "", today - timedelta(days=22), today + timedelta(days=15), "Sarah Lee",
         "Went dark after pricing call", "", "3", "in_progress"),
        ("D007", "GreenGrid", "Grace Lee", "grace@greengrid.net", 110000, "negotiation",
         "", today - timedelta(days=30), today + timedelta(days=10), "Jane Park",
         "Champion left the company", "", "0", "completed"),
        ("D008", "HyperLoop AI", "Henry Zhang", "henry@hyperloop.ai", 200000, "closing",
         "", today - timedelta(days=18), today + timedelta(days=5), "Mike Chen",
         "Budget freeze announced", "", "2", "in_progress"),

        # ★ CHURN RISKS (2) — renewal < 60 days AND (tickets > 5 OR onboarding delayed)
        ("D009", "InnoSphere", "Iris Patel", "iris@innosphere.com", 55000, "closed_won",
         "Quarterly review", today - timedelta(days=10), today + timedelta(days=90), "Sarah Lee",
         "Unhappy with response times", "45", "8", "delayed"),
        ("D010", "JetStream", "Jack Turner", "jack@jetstream.io", 88000, "closed_won",
         "Renewal discussion", today - timedelta(days=5), today + timedelta(days=60), "Jane Park",
         "Multiple escalations this quarter", "30", "12", "in_progress"),

        # More normal deals
        ("D011", "KernelSoft", "Kate Brown", "kate@kernelsoft.com", 42000, "proposal",
         "Schedule security review", today - timedelta(days=4), today + timedelta(days=35), "Mike Chen",
         "CISO wants SOC2 report", "", "0", "not_started"),
        ("D012", "LightPath", "Liam Scott", "liam@lightpath.co", 67000, "qualification",
         "Send case studies", today - timedelta(days=6), today + timedelta(days=50), "Sarah Lee",
         "Small team, fast mover", "", "1", "not_started"),
        ("D013", "MeshDynamics", "Mia Garcia", "mia@mesh.io", 150000, "negotiation",
         "Finalize MSA terms", today - timedelta(days=3), today + timedelta(days=25), "Jane Park",
         "Legal asks for data residency clause", "", "0", "completed"),
        ("D014", "NovaBridge", "Noah Kim", "noah@novabridge.com", 38000, "prospecting",
         "Discovery call", today - timedelta(days=2), today + timedelta(days=75), "Mike Chen",
         "Referral from D002", "", "0", "not_started"),
        ("D015", "Orbitra", "Olivia Chen", "olivia@orbitra.com", 85000, "closing",
         "Contract signing", today - timedelta(days=1), today + timedelta(days=7), "Sarah Lee",
         "All approvals in place", "", "0", "completed"),
        ("D016", "PulseNet", "Paul Davis", "paul@pulsenet.com", 29000, "qualification",
         "Product walkthrough", today - timedelta(days=8), today + timedelta(days=55), "Jane Park",
         "Budget constrained, looking at free tier", "", "2", "not_started"),
        ("D017", "QuantumLeap", "Quinn Roberts", "quinn@quantum.io", 175000, "proposal",
         "Executive alignment meeting", today - timedelta(days=4), today + timedelta(days=40), "Mike Chen",
         "Strong champion, multi-year potential", "", "0", "in_progress"),
        ("D018", "RippleWorks", "Rachel Adams", "rachel@ripple.works", 53000, "prospecting",
         "Send intro deck", today - timedelta(days=1), today + timedelta(days=80), "Sarah Lee",
         "Met at conference", "", "0", "not_started"),
        ("D019", "StackForge", "Sam White", "sam@stackforge.dev", 95000, "negotiation",
         "Pricing discussion", today - timedelta(days=6), today + timedelta(days=18), "Jane Park",
         "Asking for 20% discount", "", "1", "completed"),
        ("D020", "TerraNode", "Tina Lopez", "tina@terranode.com", 62000, "closing",
         "Final sign-off from CFO", today - timedelta(days=3), today + timedelta(days=12), "Mike Chen",
         "Verbal yes, waiting on paperwork", "", "0", "completed"),
    ]

    header = [
        "deal_id", "account_name", "contact_name", "contact_email", "deal_value",
        "stage", "next_step", "last_activity_date", "expected_close_date", "owner",
        "notes", "renewal_days_left", "ticket_count", "onboarding_status",
    ]

    csv_path = SAMPLE_DIR / "crm_deals.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        for d in deals:
            writer.writerow([str(v) for v in d])

    print(f"✅ Written {len(deals)} deals → {csv_path}")


# ── 2. Meeting Notes (Markdown) ────────────────────────────

MEETING_NOTES = [
    {
        "filename": "meeting_acme_corp.md",
        "content": """Account: Acme Corp
Date: {today}
Attendees: Alice Johnson, Sarah Lee, VP Engineering

# Quarterly Business Review — Acme Corp

## Discussion Points
- Alice confirmed the team is evaluating our enterprise plan alongside CompetitorX.
- Key concern: "We need better API rate-limit documentation before we can commit."
- Budget approved for Q2; decision expected within 3 weeks.

## Objections Raised
- **Pricing**: "Your per-seat pricing is 15% higher than CompetitorX for the same tier."
- **Integration**: Needs native Salesforce connector (currently only via Zapier).

## Action Items
ACTION: Send updated API documentation to Alice by end of week @SarahLee
ACTION: Prepare competitive pricing comparison vs CompetitorX @MikeChen
TODO: Schedule technical deep-dive with Acme's VP Engineering by {next_week}
- [ ] Follow up on Salesforce integration roadmap @JanePark
""",
    },
    {
        "filename": "meeting_futurescale.md",
        "content": """Account: FutureScale
Date: {week_ago}
Attendees: Frank Wilson, Sarah Lee

# Renewal Check-in — FutureScale

## Discussion Points
- Frank mentioned the team hasn't adopted the new dashboard features.
- Usage metrics show only 30% of seats are active.
- Frank was non-committal about renewal timeline.

## Objections Raised
- **Value**: "We're not seeing the ROI we expected."
- **Competitor**: "We've started evaluating RivalCo as a potential replacement."

## Action Items
ACTION: Send ROI case study for similar-sized companies @SarahLee by {next_week}
→ Schedule product training sessions for FutureScale team
- [ ] Escalate to customer success lead — urgent retention risk
""",
    },
    {
        "filename": "meeting_innosphere.md",
        "content": """Account: InnoSphere
Date: {three_days_ago}
Attendees: Iris Patel, Sarah Lee, CSM Lead

# Escalation Review — InnoSphere

## Discussion Points
- Iris expressed frustration with support response times (avg 48h vs SLA of 24h).
- Onboarding delayed due to missing SSO configuration guide.
- 8 open tickets, 3 are P1 severity.
- Renewal in 45 days — at risk.

## Objections Raised
- **Support**: "If response times don't improve, we'll have to look elsewhere."
- **Onboarding**: "We're 3 weeks behind our go-live date."

## Action Items
ACTION: Assign dedicated support engineer to InnoSphere — URGENT @SarahLee
ACTION: Send SSO configuration guide within 24 hours @MikeChen
TODO: Schedule weekly check-ins until onboarding completes
- [ ] Prepare executive apology + remediation plan for Iris
""",
    },
    {
        "filename": "meeting_meshdynamics.md",
        "content": """Account: MeshDynamics
Date: {two_days_ago}
Attendees: Mia Garcia, Jane Park, Legal Counsel

# Contract Negotiation — MeshDynamics

## Discussion Points
- Legal reviewing the MSA; data residency clause is the main sticking point.
- Mia confirmed $150K budget locked and approved.
- Target close: end of month.

## Objections Raised
- **Data Residency**: "Our EU customers require data stays in EU-West region."
- **Contract Term**: Prefer 1-year with opt-out vs our standard 2-year.

## Action Items
ACTION: Add EU-West data residency clause to MSA draft @JanePark by {next_week}
ACTION: Get approval for 1-year contract option from finance @MikeChen
- [ ] Send revised MSA to Mia's legal team for review
""",
    },
    {
        "filename": "meeting_stackforge.md",
        "content": """Account: StackForge
Date: {four_days_ago}
Attendees: Sam White, Jane Park

# Pricing Discussion — StackForge

## Discussion Points
- Sam is asking for a 20% discount on the annual plan.
- They're comparing our pricing to open-source alternatives.
- Strong technical fit — their engineering team loves the product.
- Internal champion is Sam's CTO.

## Objections Raised
- **Pricing**: "We can get 80% of the functionality from the open-source version for free."
- **Competitor**: "ToolCraft offers a similar product at 30% less."

## Action Items
ACTION: Prepare value-add bundle proposal (training + priority support) @JanePark
TODO: Get approval for 10% discount + extended payment terms @MikeChen
→ Schedule call with Sam's CTO to discuss premium features
- [ ] Draft comparison doc: our platform vs open-source alternatives
""",
    },
]


def generate_meeting_notes():
    today = date.today()
    replacements = {
        "{today}": str(today),
        "{week_ago}": str(today - timedelta(days=7)),
        "{next_week}": str(today + timedelta(days=7)),
        "{three_days_ago}": str(today - timedelta(days=3)),
        "{two_days_ago}": str(today - timedelta(days=2)),
        "{four_days_ago}": str(today - timedelta(days=4)),
    }

    for note in MEETING_NOTES:
        content = note["content"]
        for k, v in replacements.items():
            content = content.replace(k, v)
        path = SAMPLE_DIR / "meeting_notes" / note["filename"]
        path.write_text(content.strip(), encoding="utf-8")
        print(f"✅ Written → {path}")


# ── 3. Call Transcripts (JSON) ──────────────────────────────

TRANSCRIPTS = [
    {
        "filename": "transcript_acme_corp.json",
        "data": {
            "transcript_id": "T001",
            "account_name": "Acme Corp",
            "date": None,  # filled dynamically
            "messages": [
                {"speaker": "Sarah Lee", "timestamp": "00:00:15", "text": "Thanks for joining, Alice. Let's review where we are on the enterprise plan evaluation."},
                {"speaker": "Alice Johnson", "timestamp": "00:00:30", "text": "Sure. We've narrowed it down to you and CompetitorX. The main differentiator right now is pricing."},
                {"speaker": "Sarah Lee", "timestamp": "00:01:00", "text": "Understood. Can you share more about the pricing concern?"},
                {"speaker": "Alice Johnson", "timestamp": "00:01:15", "text": "CompetitorX is offering us per-seat pricing that's about 15% lower. On 200 seats, that adds up."},
                {"speaker": "Sarah Lee", "timestamp": "00:01:45", "text": "That's fair. We do provide additional value though — dedicated support, SLA guarantees, and the API layer."},
                {"speaker": "Alice Johnson", "timestamp": "00:02:10", "text": "True, but our VP of Engineering wants to see better API documentation before committing."},
                {"speaker": "Sarah Lee", "timestamp": "00:02:30", "text": "I'll have our technical writer send over the updated docs by Friday."},
                {"speaker": "Alice Johnson", "timestamp": "00:02:45", "text": "That would help. Also, any chance of a Salesforce native connector? Right now it's Zapier only."},
            ],
        },
    },
    {
        "filename": "transcript_futurescale.json",
        "data": {
            "transcript_id": "T002",
            "account_name": "FutureScale",
            "date": None,
            "messages": [
                {"speaker": "Sarah Lee", "timestamp": "00:00:10", "text": "Frank, thanks for making time. How's the team finding the platform?"},
                {"speaker": "Frank Wilson", "timestamp": "00:00:25", "text": "Honestly, adoption has been slower than we expected. Only about a third of our team uses it regularly."},
                {"speaker": "Sarah Lee", "timestamp": "00:00:50", "text": "That's concerning. What's driving the low adoption?"},
                {"speaker": "Frank Wilson", "timestamp": "00:01:10", "text": "The new dashboard features aren't intuitive. We've had to do a lot of internal training."},
                {"speaker": "Sarah Lee", "timestamp": "00:01:30", "text": "We can definitely help with that. Would product training sessions help?"},
                {"speaker": "Frank Wilson", "timestamp": "00:01:50", "text": "Maybe, but I'll be honest — we've started looking at RivalCo. Their UX is more straightforward."},
                {"speaker": "Sarah Lee", "timestamp": "00:02:15", "text": "I appreciate the candour. Let me put together an ROI analysis and schedule training."},
                {"speaker": "Frank Wilson", "timestamp": "00:02:35", "text": "Sure, but pricing is also a factor. We're not seeing the ROI we expected for what we're paying."},
            ],
        },
    },
    {
        "filename": "transcript_jetstream.json",
        "data": {
            "transcript_id": "T003",
            "account_name": "JetStream",
            "date": None,
            "messages": [
                {"speaker": "Jane Park", "timestamp": "00:00:10", "text": "Jack, I wanted to touch base on the escalations your team has raised."},
                {"speaker": "Jack Turner", "timestamp": "00:00:25", "text": "Thanks, Jane. We've had 12 tickets open this quarter, and some have been sitting for weeks."},
                {"speaker": "Jane Park", "timestamp": "00:00:45", "text": "I see that. We're assigning a dedicated engineer to handle your account going forward."},
                {"speaker": "Jack Turner", "timestamp": "00:01:05", "text": "That helps. But our renewal is in 30 days and frankly, my leadership is questioning the investment."},
                {"speaker": "Jane Park", "timestamp": "00:01:25", "text": "Completely understand. What would it take to restore confidence?"},
                {"speaker": "Jack Turner", "timestamp": "00:01:45", "text": "Pricing adjustment would be a start. We've seen competitor offers from RivalCo that are 25% less."},
                {"speaker": "Jane Park", "timestamp": "00:02:05", "text": "Let me take that back to our team and come back with a retention offer."},
                {"speaker": "Jack Turner", "timestamp": "00:02:20", "text": "Also, the onboarding for our new modules is behind. That's affecting our go-live timeline."},
            ],
        },
    },
    {
        "filename": "transcript_quantumleap.json",
        "data": {
            "transcript_id": "T004",
            "account_name": "QuantumLeap",
            "date": None,
            "messages": [
                {"speaker": "Mike Chen", "timestamp": "00:00:10", "text": "Quinn, exciting to discuss the multi-year engagement. Your CTO seemed very positive last week."},
                {"speaker": "Quinn Roberts", "timestamp": "00:00:30", "text": "She is. But we need to address pricing before we can get budget approval for a 3-year commitment."},
                {"speaker": "Mike Chen", "timestamp": "00:00:55", "text": "What pricing structure works best for your team?"},
                {"speaker": "Quinn Roberts", "timestamp": "00:01:15", "text": "We'd like a volume discount. At 500+ seats, per-seat pricing needs to come down."},
                {"speaker": "Mike Chen", "timestamp": "00:01:35", "text": "We can definitely explore tiered pricing. What's the competitor landscape look like for you?"},
                {"speaker": "Quinn Roberts", "timestamp": "00:01:55", "text": "We've been approached by MegaSuite. Their enterprise offering is aggressive on pricing."},
                {"speaker": "Mike Chen", "timestamp": "00:02:15", "text": "MegaSuite has a different architecture that doesn't scale the same way. Let me put together a TCO comparison."},
                {"speaker": "Quinn Roberts", "timestamp": "00:02:35", "text": "That would be great. Also send the executive summary deck — I need to present to the board next week."},
            ],
        },
    },
    {
        "filename": "transcript_stackforge.json",
        "data": {
            "transcript_id": "T005",
            "account_name": "StackForge",
            "date": None,
            "messages": [
                {"speaker": "Jane Park", "timestamp": "00:00:10", "text": "Sam, let's dig into the pricing discussion. You mentioned a 20% discount request."},
                {"speaker": "Sam White", "timestamp": "00:00:25", "text": "Right. We love the product — our engineers are very happy with it. But financially, we're comparing to open-source."},
                {"speaker": "Jane Park", "timestamp": "00:00:50", "text": "Open-source doesn't come with SLA, support, or the managed infrastructure we provide."},
                {"speaker": "Sam White", "timestamp": "00:01:10", "text": "True, but our CTO estimates we can get 80% of the functionality from the open-source version."},
                {"speaker": "Jane Park", "timestamp": "00:01:30", "text": "That last 20% is usually where the production reliability lives. Let me build a comparison doc."},
                {"speaker": "Sam White", "timestamp": "00:01:50", "text": "Also, ToolCraft reached out. They're offering similar functionality at about 30% less."},
                {"speaker": "Jane Park", "timestamp": "00:02:10", "text": "ToolCraft doesn't have our observability features. What if we bundled training and priority support?"},
                {"speaker": "Sam White", "timestamp": "00:02:30", "text": "That could work. But I need at least a 10% discount to take back to procurement."},
            ],
        },
    },
]


def generate_transcripts():
    today = date.today()
    for t in TRANSCRIPTS:
        data = t["data"].copy()
        data["date"] = str(today - timedelta(days=TRANSCRIPTS.index(t) + 1))
        path = SAMPLE_DIR / "transcripts" / t["filename"]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"✅ Written → {path}")


# ── 4. Persist seed data to SQLite ──────────────────────────

def persist_to_db():
    """
    Parse all generated seed files and INSERT them directly into SQLite.
    Uses explicit session.commit() and verifies the inserts.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    from app.config import settings
    from app.db.models import (
        Base, Deal, MeetingNoteRecord, TranscriptRecord,
        engine, SessionLocal, init_db,
    )
    from app.ingest.csv_parser import parse_csv
    from app.ingest.text_parser import parse_meeting_note, parse_transcript_json

    # Show which DB file we're targeting
    db_url = str(settings.database_url)
    print(f"\n🗄️  Database URL: {db_url}")

    # Create all tables
    init_db()
    print("   Tables created ✅")

    # ── Open session and persist ───────────────────────────
    session = SessionLocal()

    try:
        # --- Deals from CSV ---
        csv_path = SAMPLE_DIR / "crm_deals.csv"
        if csv_path.exists():
            records = parse_csv(csv_path)
            print(f"\n   Parsed {len(records)} deal records from CSV")

            for rec in records:
                existing = session.query(Deal).filter_by(deal_id=rec.deal_id).first()
                if existing:
                    print(f"   ⏭️  Deal {rec.deal_id} already exists, updating...")
                    existing.account_name = rec.account_name
                    existing.deal_value = rec.deal_value
                    existing.stage = rec.stage.value
                    existing.next_step = rec.next_step
                    existing.last_activity_date = rec.last_activity_date
                    existing.owner = rec.owner
                else:
                    deal = Deal(
                        deal_id=rec.deal_id,
                        account_name=rec.account_name,
                        contact_name=rec.contact_name,
                        contact_email=rec.contact_email,
                        deal_value=rec.deal_value,
                        stage=rec.stage.value,
                        next_step=rec.next_step,
                        last_activity_date=rec.last_activity_date,
                        expected_close_date=rec.expected_close_date,
                        owner=rec.owner,
                        notes=rec.notes,
                        renewal_days_left=rec.renewal_days_left,
                        ticket_count=rec.ticket_count,
                        onboarding_status=rec.onboarding_status.value if rec.onboarding_status else None,
                    )
                    session.add(deal)

            session.commit()
            deal_count = session.query(Deal).count()
            print(f"   📊 Deals in DB after commit: {deal_count}")

        # --- Meeting Notes ---
        notes_dir = SAMPLE_DIR / "meeting_notes"
        if notes_dir.exists():
            for f in sorted(notes_dir.glob("*.md")):
                note = parse_meeting_note(f)
                exists = session.query(MeetingNoteRecord).filter_by(note_id=note.note_id).first()
                if not exists:
                    session.add(MeetingNoteRecord(
                        note_id=note.note_id,
                        account_name=note.account_name,
                        date=note.date,
                        attendees=", ".join(note.attendees),
                        content=note.content,
                        source_file=note.source_file,
                    ))

            session.commit()
            note_count = session.query(MeetingNoteRecord).count()
            print(f"   📝 Meeting notes in DB after commit: {note_count}")

        # --- Transcripts ---
        transcripts_dir = SAMPLE_DIR / "transcripts"
        if transcripts_dir.exists():
            for f in sorted(transcripts_dir.glob("*.json")):
                t = parse_transcript_json(f)
                exists = session.query(TranscriptRecord).filter_by(transcript_id=t.transcript_id).first()
                if not exists:
                    full_text = "\n".join(f"{m.speaker}: {m.text}" for m in t.messages)
                    session.add(TranscriptRecord(
                        transcript_id=t.transcript_id,
                        account_name=t.account_name,
                        date=t.date,
                        full_text=full_text,
                        source_file=t.source_file,
                    ))

            session.commit()
            transcript_count = session.query(TranscriptRecord).count()
            print(f"   🎙️  Transcripts in DB after commit: {transcript_count}")

    except Exception as e:
        session.rollback()
        print(f"\n   ❌ ERROR during DB persist: {e}")
        raise
    finally:
        session.close()


# ── Main ────────────────────────────────────────────────────

def main():
    _ensure_dirs()

    # Step 1: Generate files
    generate_crm_csv()
    generate_meeting_notes()
    generate_transcripts()
    print(f"\n📁 All seed files generated in: {SAMPLE_DIR}")

    # Step 2: Persist to SQLite
    persist_to_db()

    print("\n🎉 Done! Database is seeded and ready.")
    print("   Run: python check_setup.py             (to verify)")
    print("   Run: streamlit run frontend/dashboard.py")


if __name__ == "__main__":
    main()

