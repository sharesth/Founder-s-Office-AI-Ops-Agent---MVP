"""
Streamlit Dashboard — Founder's Office AI Ops Agent

Features:
  • KPI cards (pipeline summary)
  • Pipeline Blockers table with evidence
  • Churn Watchlist with risk levels and evidence
  • Action Items tracker
  • Sidebar: Email Drafter
  • Sidebar: Ask the Agent (natural-language Q&A)
"""

from __future__ import annotations

import sys
import os
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import requests

from app.db.models import init_db, SessionLocal
from app.tools.pipeline import get_pipeline_summary, get_stalled_deals
from app.tools.churn import get_churn_watchlist
from app.tools.actions import extract_all_action_items
from app.agents.orchestrator import ask_question, draft_email


# ── Page Config ────────────────────────────────────────────

st.set_page_config(
    page_title="Founder's Office · AI Ops",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Custom CSS ─────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main .block-container { padding-top: 1.5rem; max-width: 1200px; }

    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        transition: transform 0.2s ease;
    }
    .kpi-card:hover { transform: translateY(-4px); }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #00d2ff 0%, #7b2ff7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .kpi-label { font-size: 0.85rem; color: #a0aec0; text-transform: uppercase; letter-spacing: 1px; }

    /* Risk badges */
    .risk-critical { background: #ff4136; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .risk-high { background: #ff851b; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .risk-medium { background: #ffdc00; color: #333; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .risk-low { background: #2ecc40; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }

    /* Section headers */
    .section-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #7b2ff7;
    }
</style>
""", unsafe_allow_html=True)


# ── Init DB session ────────────────────────────────────────

init_db()
db = SessionLocal()

# Debug: verify we're connected to the right DB with data
from app.config import settings
from app.db.models import Deal

_deal_count = db.query(Deal).count()
if _deal_count == 0:
    st.warning(
        "**Database is empty!** No deals found. "
        "Run `python seed_data.py` from the `founders_office_ai_ops/` directory first, "
        "then refresh this page."
    )
    st.info(f"DB URL: `{settings.database_url}`")


# ── Header ─────────────────────────────────────────────────

st.markdown("# Founder's Office · AI Ops Agent")
st.markdown("*Pipeline intelligence, churn detection, and AI-powered insights — all in one place.*")
st.divider()


# ── KPI Cards ──────────────────────────────────────────────

summary = get_pipeline_summary(db)

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{summary.total_deals}</div>
        <div class="kpi-label">Total Deals</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">${summary.total_pipeline_value:,.0f}</div>
        <div class="kpi-label">Pipeline Value</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">${summary.avg_deal_value:,.0f}</div>
        <div class="kpi-label">Avg Deal Size</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{summary.stalled_count}</div>
        <div class="kpi-label">Stalled</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{summary.closing_without_next_step}</div>
        <div class="kpi-label">No Next Step</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    churn_risks = get_churn_watchlist(db)
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{len(churn_risks)}</div>
        <div class="kpi-label">Churn Risks</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Pipeline Blockers ─────────────────────────────────────

st.markdown('<div class="section-header">Pipeline Blockers</div>', unsafe_allow_html=True)

blockers = get_stalled_deals(db)

if blockers:
    blocker_data = []
    for b in blockers:
        risk_badge = f'<span class="risk-{b.risk_level.value}">{b.risk_level.value.upper()}</span>'
        evidence_text = "; ".join(e.snippet[:100] for e in b.evidence) if b.evidence else "—"
        blocker_data.append({
            "Account": b.account_name.title(),
            "Deal ID": b.deal_id,
            "Risk": b.risk_level.value.upper(),
            "Days Inactive": b.days_inactive or "—",
            "Rule Triggered": b.rule_triggered,
            "Recommended Action": b.recommended_action or "—",
        })

    df_blockers = pd.DataFrame(blocker_data)
    st.dataframe(df_blockers, use_container_width=True, hide_index=True)

    with st.expander("Blocker Evidence Details"):
        for b in blockers:
            st.markdown(f"**{b.account_name.title()}** — {b.description}")
            for e in b.evidence:
                st.markdown(f"  - *{e.source}*: `{e.snippet[:200]}`")
            st.markdown("---")
else:
    st.success("No pipeline blockers detected!")


# ── Churn Watchlist ────────────────────────────────────────

st.markdown('<div class="section-header">Churn Watchlist</div>', unsafe_allow_html=True)

if churn_risks:
    churn_data = []
    for r in churn_risks:
        churn_data.append({
            "Account": r.account_name.title(),
            "Risk Level": r.risk_level.value.upper(),
            "Renewal (days)": r.renewal_days_left or "—",
            "Open Tickets": r.ticket_count or 0,
            "Onboarding": r.onboarding_status.value if r.onboarding_status else "—",
            "Reasons": " | ".join(r.reasons),
        })

    df_churn = pd.DataFrame(churn_data)
    st.dataframe(df_churn, use_container_width=True, hide_index=True)

    with st.expander("Churn Evidence Details"):
        for r in churn_risks:
            st.markdown(f"**{r.account_name.title()}** — Risk: {r.risk_level.value.upper()}")
            for e in r.evidence:
                st.markdown(f"  - *{e.source}*: `{e.snippet[:200]}`")
            if r.recommended_action:
                st.info(f"**Recommended**: {r.recommended_action}")
            st.markdown("---")
else:
    st.success("No churn risks detected!")


# ── Action Items ───────────────────────────────────────────

st.markdown('<div class="section-header">Action Items</div>', unsafe_allow_html=True)

actions = extract_all_action_items(db)

if actions:
    action_data = []
    for a in actions:
        action_data.append({
            "Account": a.account_name.title(),
            "Action": a.description,
            "Owner": a.owner or "—",
            "Priority": a.priority.value.upper(),
            "Due Date": str(a.due_date) if a.due_date else "—",
            "Source": a.source,
        })

    df_actions = pd.DataFrame(action_data)
    st.dataframe(df_actions, use_container_width=True, hide_index=True)
else:
    st.info("No action items extracted yet. Ingest meeting notes or transcripts first.")


# ── Deals by Stage (bar chart) ─────────────────────────────

st.markdown('<div class="section-header">Deals by Stage</div>', unsafe_allow_html=True)

if summary.deals_by_stage:
    stage_df = pd.DataFrame(
        list(summary.deals_by_stage.items()),
        columns=["Stage", "Count"]
    )
    st.bar_chart(stage_df.set_index("Stage"))


# ── Sidebar: Email Drafter ─────────────────────────────────

st.sidebar.markdown("## Email Drafter")

with st.sidebar.form("email_form"):
    email_account = st.text_input("Account Name", placeholder="e.g. acme corp")
    email_to = st.text_input("Recipient Email", placeholder="alice@acme.com")
    email_purpose = st.text_area("Purpose", placeholder="Follow up on pricing discussion...")
    email_tone = st.selectbox("Tone", ["professional", "warm", "urgent"])
    email_submit = st.form_submit_button("Draft Email")

if email_submit and email_account and email_to:
    with st.sidebar:
        with st.spinner("Drafting email with AI..."):
            email_result = draft_email(email_account, email_to, email_purpose, db, tone=email_tone)
        st.markdown(f"**Subject:** {email_result.subject}")
        st.markdown("**Body:**")
        st.text_area("Body", email_result.body, height=450, label_visibility="collapsed")
        if email_result.evidence:
            with st.expander("Evidence"):
                for e in email_result.evidence:
                    st.markdown(f"- *{e.source}*: {e.snippet[:150]}")


# ── Sidebar: Ask the Agent ─────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.markdown("## Ask the Agent")

with st.sidebar.form("ask_form"):
    question = st.text_area("Your Question", placeholder="Which deals are at risk this week?")
    ask_submit = st.form_submit_button("Ask")

if ask_submit and question:
    with st.sidebar:
        with st.spinner("Thinking..."):
            answer = ask_question(question, db)
        st.markdown(f"**Answer**: {answer.answer}")
        if answer.evidence:
            with st.expander("Evidence"):
                for e in answer.evidence:
                    st.markdown(f"- *{e.source}*: {e.snippet[:150]}")


# ── 3. Document Ingest ─────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.header("Ingest Documents")

API_URL = "http://localhost:8000/api/v1"

uploaded_file = st.sidebar.file_uploader(
    "Upload Meeting Note or Transcript", 
    type=["md", "txt", "json"],
    help="Upload .md/.txt (meeting notes) or .json (transcripts) to add to the knowledge base."
)

if uploaded_file is not None:
    if st.sidebar.button("Process & Ingest Content"):
        with st.sidebar.spinner("Uploading and parsing..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                resp = requests.post(f"{API_URL}/ingest/upload", files=files)
                if resp.status_code == 200:
                    st.sidebar.success(f"Successfully ingested: {uploaded_file.name}")
                    st.sidebar.info("Tip: Rebuild the index below to enable AI retrieval.")
                else:
                    st.sidebar.error(f"Ingest failed: {resp.text}")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

if st.sidebar.button("Rebuild Vector Index"):
    with st.sidebar.spinner("Rebuilding FAISS index..."):
        try:
            resp = requests.post(f"{API_URL}/ingest/build-index")
            if resp.status_code == 200:
                data = resp.json()
                st.sidebar.success(f"Index rebuilt! {data.get('documents_indexed', 0)} docs indexed.")
            else:
                st.sidebar.error("Failed to rebuild index.")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")


# ── Cleanup ────────────────────────────────────────────────

db.close()
