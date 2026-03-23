# 📋 Product Requirements Document (PRD)
## Founder's Office AI Ops Agent — MVP

**Version:** 1.0  
**Date:** 2026-03-23  
**Author:** Ankush Sharesth  

---

## 1. Product Overview

The **Founder's Office AI Ops Agent** is an AI-powered operations assistant built for startup founders and revenue leaders. It ingests real sales data — CRM exports, meeting notes, and call transcripts — and surfaces actionable insights like pipeline blockers, churn risks, and follow-up tasks.

### What makes it different?
It uses a **hybrid intelligence approach**: deterministic business rules catch known patterns instantly, while Google Gemini (LLM) provides deeper reasoning, natural-language Q&A, and email drafting — all grounded in evidence.

---

## 2. Problem Statement

Startup founders waste 5–10 hours/week manually reviewing CRM data, meeting notes, and call logs to answer questions like:
- *"Which deals have gone silent?"*
- *"Are any customers about to churn?"*
- *"What action items are falling through the cracks?"*

This agent **automates that entire workflow** in seconds.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT DASHBOARD                       │
│  KPI Cards │ Blockers │ Churn │ Actions │ Email │ Q&A       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     FastAPI BACKEND                          │
│  /ingest/upload  │  /pipeline/*  │  /churn  │  /ask  │ etc  │
└──────┬───────────────────┬──────────────────┬───────────────┘
       │                   │                  │
┌──────▼──────┐  ┌─────────▼────────┐  ┌─────▼──────────────┐
│  INGESTION  │  │ DETERMINISTIC    │  │ LLM ORCHESTRATOR   │
│  ENGINE     │  │ TOOLS            │  │ (Google Gemini)     │
│             │  │                  │  │                     │
│ CSV Parser  │  │ Stalled Deals    │  │ Q&A with context    │
│ MD  Parser  │  │ Churn Watchlist  │  │ Email drafting      │
│ JSON Parser │  │ Action Extractor │  │ Action extraction   │
└──────┬──────┘  └────────┬─────────┘  └──────┬──────────────┘
       │                  │                   │
┌──────▼──────────────────▼───────────────────▼──────────────┐
│                    DATA LAYER                               │
│  SQLite (SQLAlchemy 2.0)  │  FAISS Vector Index            │
│  Deals, Notes, Transcripts│  Semantic search via Gemini    │
│                           │  text-embedding-004            │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Folder Structure

```
founders_office_ai_ops/
├── app/
│   ├── api/routes.py          # FastAPI endpoints
│   ├── agents/orchestrator.py # LLM calls (Gemini 2.5 Flash)
│   ├── tools/
│   │   ├── pipeline.py        # Stalled deals, pipeline summary
│   │   ├── churn.py           # Churn watchlist
│   │   └── actions.py         # Action item extraction (regex)
│   ├── ingest/
│   │   ├── csv_parser.py      # CRM CSV → DealRecord objects
│   │   ├── text_parser.py     # Meeting notes & transcript parser
│   │   └── normalizer.py      # Name, date, email normalization
│   ├── retrieval/
│   │   └── hybrid.py          # SQL queries + FAISS vector search
│   ├── db/
│   │   └── models.py          # SQLAlchemy ORM (Deal, Note, Transcript)
│   ├── schemas.py             # All Pydantic v2 models
│   ├── config.py              # Settings from .env
│   └── main.py                # FastAPI app entrypoint
├── frontend/
│   └── dashboard.py           # Streamlit UI
├── data/sample/               # Generated seed data
├── seed_data.py               # Generates 20 deals, 5 notes, 5 transcripts
├── check_setup.py             # Verifies API key, embeddings, and DB
├── requirements.txt
└── .env                       # GOOGLE_API_KEY, DB URL, etc.
```

---

## 5. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Python 3.10+, FastAPI | REST API, async routing |
| **Frontend** | Streamlit | Interactive dashboard |
| **Database** | SQLite + SQLAlchemy 2.0 | Structured data (deals, notes, transcripts) |
| **Vector Store** | FAISS (faiss-cpu) | Semantic similarity search |
| **LLM** | Google Gemini 2.5 Flash | Q&A, email drafting, action extraction |
| **Embeddings** | text-embedding-004 (Google, API v1) | Vector embeddings for FAISS |
| **Validation** | Pydantic v2 | Schema enforcement, data normalization |
| **Data Processing** | Pandas | CSV ingestion and transformation |

---

## 6. Data Sources & Ingestion

### 6.1 CRM Export (CSV)
- **Input:** CSV file with columns like `deal_id`, `account_name`, `deal_value`, `stage`, `next_step`, `last_activity_date`, etc.
- **Processing:** Column names are fuzzy-matched (e.g., `"company"` → `account_name`), dates normalized, account names lowercased.
- **Output:** `Deal` rows in SQLite.

### 6.2 Meeting Notes (Markdown / TXT)
- **Input:** `.md` or `.txt` files with a header block (`Account:`, `Date:`, `Attendees:`) and free-form notes.
- **Processing:** Regex extracts metadata; full content stored for semantic search and action item extraction.
- **Output:** `MeetingNoteRecord` rows in SQLite + indexed in FAISS.

### 6.3 Call Transcripts (JSON / TXT)
- **Input:** JSON with `transcript_id`, `account_name`, `date`, and `messages[]` array.
- **Processing:** Messages flattened into `speaker: text` format for search.
- **Output:** `TranscriptRecord` rows in SQLite + indexed in FAISS.

---

## 7. Core Business Rules (Deterministic)

These run **instantly** with zero LLM cost — pure Python logic:

### Rule 1: Stalled Deal Detection
```
IF last_activity_date > 14 days ago  OR  next_step is NULL/empty
THEN → Flag as STALLED DEAL
```
- Risk level auto-calculated based on days inactive (>30 = critical, >21 = high, >14 = medium)

### Rule 2: Churn Risk Detection
```
IF renewal_days_left < 60
   AND (ticket_count > 5  OR  onboarding_status == "delayed")
THEN → Flag as CHURN RISK
```
- Accounts with both conditions get `CRITICAL` risk level

### Rule 3: Missing Data Quality
```
IF stage == "closing"  AND  next_step is NULL
THEN → Flag as "closing_without_next_step"
```

---

## 8. LLM Features (Google Gemini)

All LLM responses are **strictly JSON** with mandatory `evidence` snippets — **no hallucination allowed**.

### 8.1 Ask the Agent (Q&A)
- User types a natural-language question (e.g., *"Which deals mention competitor pricing?"*)
- System retrieves context via **hybrid retrieval** (SQL + FAISS vector search)
- Gemini answers based solely on retrieved evidence

### 8.2 Email Drafter
- User provides: account name, recipient, purpose, tone
- System retrieves all relevant context for that account
- Gemini drafts a professional follow-up email grounded in real data

### 8.3 LLM Action Extraction (Fallback)
- When regex heuristics miss action items, Gemini extracts them from text
- Each action includes: description, owner, due date, priority, and the evidence snippet

---

## 9. Hybrid Retrieval System

The retrieval layer combines two approaches:

| Method | What it does | When it's used |
|--------|-------------|----------------|
| **SQL Queries** | Exact lookups on deals, notes by account name, stage, dates | Structured questions, pipeline analysis |
| **FAISS Vector Search** | Semantic similarity using Gemini `text-embedding-004` | Free-form questions, finding related conversations |

Results from both are merged and passed as context to the LLM.

---

## 10. Streamlit Dashboard Features

### Main Page
| Section | Description |
|---------|-------------|
| **KPI Cards** | 6 gradient cards: Total Deals, Pipeline Value, Avg Deal Size, Stalled Count, Missing Next Step, Churn Risks |
| **Pipeline Blockers Table** | All stalled deals with risk level, days inactive, rule triggered, recommended action |
| **Churn Watchlist Table** | At-risk accounts with renewal countdown, ticket count, onboarding status |
| **Action Items Table** | Extracted tasks with owner, priority, due date, source file |
| **Deals by Stage Chart** | Bar chart visualization of deal distribution |

### Sidebar
| Feature | Description |
|---------|-------------|
| **✉️ Email Drafter** | Form: account, recipient, purpose, tone → AI-generated email |
| **🤖 Ask the Agent** | Free-text Q&A → evidence-backed answer |

---

## 11. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ingest/upload` | Upload CSV/MD/JSON files |
| `POST` | `/api/v1/ingest/build-index` | Build FAISS vector index |
| `GET` | `/api/v1/pipeline/summary` | Pipeline KPIs |
| `GET` | `/api/v1/pipeline/blockers` | Stalled deals list |
| `GET` | `/api/v1/churn/watchlist` | Churn risk accounts |
| `GET` | `/api/v1/actions` | Extracted action items |
| `POST` | `/api/v1/ask` | Natural-language Q&A |
| `POST` | `/api/v1/email/draft` | AI email drafting |

**API Docs:** http://localhost:8000/docs (Swagger UI)

---

## 12. Seed Data (Built-in)

`seed_data.py` generates realistic sample data:

| Data Type | Count | Details |
|-----------|-------|---------|
| CRM Deals | 20 | Including 3 stalled deals (D006, D007, D008) and 2 churn risks (D009, D010) |
| Meeting Notes | 5 | For Acme Corp, FutureScale, InnoSphere, MeshDynamics, StackForge |
| Call Transcripts | 5 | Realistic dialogues with pricing/competitor objections |

---

## 13. Environment Configuration

```env
# .env file
GOOGLE_API_KEY=your-key-here      # Google AI Studio API key
GEMINI_MODEL=gemini-2.5-flash     # Text generation model
DATABASE_URL=sqlite:///./founders_ops.db
FAISS_INDEX_PATH=./faiss_index
APP_ENV=development
LOG_LEVEL=INFO
```

---

## 14. How to Run

```bash
# 1. Install dependencies (no torch — lightweight!)
pip install -r requirements.txt

# 2. Seed the database with sample data
python seed_data.py

# 3. Verify everything works
python check_setup.py

# 4. Start the API server
uvicorn app.main:app --reload --port 8000

# 5. Start the dashboard (new terminal)
streamlit run frontend/dashboard.py
```

---

## 15. Data Flow Diagram

```
CSV/MD/JSON files
       │
       ▼
┌─────────────┐     ┌──────────────┐
│  Ingestion   │────▶│   SQLite DB  │
│  (parse +    │     │  (structured │
│   normalize) │     │   storage)   │
└─────────────┘     └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Build FAISS │
                    │  Index       │
                    │  (embeddings │
                    │   via Gemini)│
                    └──────┬───────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐   ┌──────────────┐   ┌─────────────────┐
│ Deterministic│   │   Hybrid     │   │  LLM Agent      │
│ Rules        │   │   Retrieval  │   │  (Gemini)       │
│              │   │   (SQL+FAISS)│   │                 │
│ • Stalled    │   │              │   │ • Q&A           │
│ • Churn      │   │  Provides    │   │ • Email draft   │
│ • Missing    │   │  context ───▶│   │ • Actions       │
│   data       │   │              │   │                 │
└──────┬──────┘   └──────────────┘   └────────┬────────┘
       │                                      │
       └──────────────┬───────────────────────┘
                      ▼
            ┌───────────────────┐
            │  Streamlit UI     │
            │  (Dashboard +     │
            │   Sidebar tools)  │
            └───────────────────┘
```

---

## 16. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Hybrid (Rules + LLM)** | Rules are free, instant, and deterministic. LLM adds flexibility for unstructured queries. |
| **No torch dependency** | Embeddings via Google API instead of local models — install is <30 seconds vs 10+ minutes |
| **SQLite** | Zero-config, single-file DB perfect for MVP. Easy to migrate to Postgres later. |
| **FAISS** | In-memory vector search, no external service needed. Scales to ~100K documents easily. |
| **Strict JSON output** | LLM responses are `response_mime_type="application/json"` — no parsing ambiguity. |
| **Evidence-first** | Every insight must cite its source — prevents hallucination and builds trust. |
| **API v1 for embeddings** | `text-embedding-004` lives on Google's v1 API; text generation uses v1beta. Separate clients handle this. |

---

## 17. Future Enhancements (Post-MVP)

- [ ] **Scheduled reports** — Auto-generate weekly ops summaries via email
- [ ] **Slack integration** — Push alerts for stalled deals and churn risks
- [ ] **Multi-user auth** — Role-based access for founders vs. sales reps
- [ ] **PostgreSQL migration** — For production-scale deployments
- [ ] **Real-time CRM sync** — Salesforce/HubSpot webhooks instead of CSV uploads
- [ ] **Custom rules engine** — UI for founders to define their own business rules
- [ ] **Deal scoring model** — ML-based win probability predictions

---

*Built with ❤️ as an MVP for startup operations intelligence.*
