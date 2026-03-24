"""
LLM Orchestration Agent for the Founder's Office AI Ops platform.
Uses the NEW google-genai SDK (v1.0+) with `from google import genai`.

Responsibilities:
  • Answer natural-language questions using hybrid retrieval context.
  • Generate follow-up emails grounded in evidence.
  • Extract action items via LLM when deterministic extraction misses items.

All LLM responses are constrained to strict JSON via system prompts.
Every insight includes an "evidence" snippet → no hallucinated CRM values.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.retrieval.hybrid import HybridRetriever
from app.schemas import (
    ActionItem,
    ActionPriority,
    ActionStatus,
    AskResponse,
    Evidence,
    FollowUpEmail,
)

logger = logging.getLogger(__name__)


# ── Prompt templates ───────────────────────────────────────

SYSTEM_PROMPT = """You are an AI operations assistant for startup founders.
You analyse CRM data, meeting notes, and call transcripts to provide
actionable insights.

RULES:
1. NEVER hallucinate CRM values. Only reference data from the provided context.
2. Every insight MUST include an "evidence" field with a verbatim snippet
   from the source data.
3. Respond ONLY in valid JSON matching the requested schema.
4. Be concise, specific, and action-oriented.
"""

QA_PROMPT = """Given the following context about deals, meeting notes, and transcripts,
answer the user's question.

=== CONTEXT ===
{context}
=== END CONTEXT ===

USER QUESTION: {question}

Respond in this exact JSON format:
{{
  "answer": "<your concise answer>",
  "evidence": [
    {{
      "source": "<file or record name>",
      "snippet": "<verbatim excerpt from the context>",
      "relevance": "<why this evidence matters>"
    }}
  ]
}}
"""

EMAIL_PROMPT = """Draft a professional follow-up email for the account described below.
Use ONLY information from the provided context. Do NOT invent any facts.

=== CONTEXT ===
{context}
=== END CONTEXT ===

Account: {account_name}
Recipient: {to}
Tone: {tone}
Purpose: {purpose}

Respond in this exact JSON format:
{{
  "subject": "<email subject>",
  "body": "<email body>",
  "evidence": [
    {{
      "source": "<source>",
      "snippet": "<verbatim excerpt>",
      "relevance": "<why>"
    }}
  ]
}}
"""

ACTION_EXTRACTION_PROMPT = """Extract action items from the following text.
Return ONLY items explicitly mentioned. Do NOT invent tasks.

=== TEXT ===
{text}
=== END TEXT ===

Respond in this exact JSON format:
{{
  "actions": [
    {{
      "description": "<what needs to be done>",
      "owner": "<who is responsible, or null>",
      "due_date": "<YYYY-MM-DD or null>",
      "priority": "<low|medium|high|urgent>",
      "evidence_snippet": "<verbatim text that mentions this action>"
    }}
  ]
}}
"""


# ── Google GenAI client (new SDK v1.0+) ────────────────────

_client = None


def _get_client():
    """Lazy-init the google.genai.Client."""
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=settings.google_api_key)
    return _client


def _call_llm(system: str, user: str) -> str:
    """Call Google Gemini via the new google-genai SDK with JSON output."""
    try:
        from google.genai import types

        client = _get_client()

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.2,
                max_output_tokens=2000,
                response_mime_type="application/json",
            ),
        )
        return response.text

    except Exception as exc:
        logger.error("Gemini LLM call failed: %s", exc)
        return json.dumps({
            "answer": f"LLM unavailable ({type(exc).__name__}: {exc}). Please check your GOOGLE_API_KEY.",
            "evidence": [],
        })


def _parse_json(raw: str) -> dict:
    """Robustly parse JSON from LLM, stripping markdown code blocks and providing regex fallback."""
    text = raw.strip()
    if text.startswith("```"):
        # Strip ```json and ```
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("JSON parsing failed, attempting regex fallback for %s...", text[:50])
        # Fallback: extract subject and body via regex if the JSON is truncated or missing quotes
        res = {}
        # Match "field": "value" with support for unclosed quotes at the end
        for field in ["subject", "body"]:
            # Robust regex to find the field and its value, even if terminal quotes are missing
            match = re.search(f'"{field}"\s*:\s*"(.*?)(?:"|\Z)', text, re.DOTALL)
            if match:
                val = match.group(1).strip()
                # If there's a trailing quote that the non-greedy match didn't catch, or if it ended early
                res[field] = val.replace('\\n', '\n').strip()
        
        return res


# ── Public API ─────────────────────────────────────────────

def ask_question(question: str, db: Session, account_name: Optional[str] = None) -> AskResponse:
    """Answer a natural-language question using hybrid retrieval + LLM."""
    retriever = HybridRetriever(db)
    ctx = retriever.query(question, account_name=account_name)

    context_str = json.dumps(ctx, indent=2, default=str)
    prompt = QA_PROMPT.format(context=context_str, question=question)
    raw = _call_llm(SYSTEM_PROMPT, prompt)

    parsed = _parse_json(raw)
    if not parsed:
        parsed = {"answer": raw, "evidence": []}

    evidence = [
        Evidence(
            source=e.get("source", ""),
            snippet=e.get("snippet", ""),
            relevance=e.get("relevance"),
        )
        for e in parsed.get("evidence", [])
    ]

    answer_text = parsed.get("answer", "")
    if isinstance(answer_text, str):
        answer_text = answer_text.replace("\\n", "\n")

    return AskResponse(answer=answer_text, evidence=evidence)


def draft_email(
    account_name: str,
    to: str,
    purpose: str,
    db: Session,
    tone: str = "professional",
) -> FollowUpEmail:
    """Generate a follow-up email grounded in retrieval context."""
    retriever = HybridRetriever(db)
    ctx = retriever.query(purpose, account_name=account_name)

    context_str = json.dumps(ctx, indent=2, default=str)
    prompt = EMAIL_PROMPT.format(
        context=context_str,
        account_name=account_name,
        to=to,
        tone=tone,
        purpose=purpose,
    )
    raw = _call_llm(SYSTEM_PROMPT, prompt)

    parsed = _parse_json(raw)
    if not parsed:
        parsed = {"subject": "Follow Up", "body": raw, "evidence": []}
    
    body = parsed.get("body", "")
    # Ensure literal \n from LLM are handled as actual newlines if they were escaped
    if isinstance(body, str):
        body = body.replace("\\n", "\n")


    evidence = [
        Evidence(
            source=e.get("source", ""),
            snippet=e.get("snippet", ""),
            relevance=e.get("relevance"),
        )
        for e in parsed.get("evidence", [])
    ]

    return FollowUpEmail(
        email_id=f"EML-{uuid.uuid4().hex[:8]}",
        account_name=account_name,
        to=to,
        subject=parsed.get("subject", "Follow Up"),
        body=body,
        tone=tone,
        evidence=evidence,
    )


def llm_extract_actions(text: str, account_name: str, source: str) -> list[ActionItem]:
    """Use LLM to extract action items when regex heuristics miss them."""
    prompt = ACTION_EXTRACTION_PROMPT.format(text=text[:4000])
    raw = _call_llm(SYSTEM_PROMPT, prompt)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []

    items = []
    for a in parsed.get("actions", []):
        items.append(ActionItem(
            action_id=f"ACT-{uuid.uuid4().hex[:8]}",
            account_name=account_name,
            description=a.get("description", ""),
            owner=a.get("owner"),
            due_date=a.get("due_date"),
            priority=ActionPriority(a.get("priority", "medium")),
            status=ActionStatus.PENDING,
            source=source,
            evidence=[Evidence(
                source=source,
                snippet=a.get("evidence_snippet", ""),
                relevance="LLM-extracted action item",
            )] if a.get("evidence_snippet") else [],
        ))
    return items
