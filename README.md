# 🚀 Founder's Office AI Ops Agent

An AI-powered operations assistant for startup founders that ingests CRM exports, meeting notes, and call transcripts to surface **pipeline blockers**, **churn risks**, and **action items** — using a hybrid approach of deterministic business rules + Google Gemini LLM reasoning.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?logo=streamlit)
![Gemini](https://img.shields.io/badge/Google-Gemini_2.5-yellow?logo=google)

---

## ✨ Features

| Feature | Type | Description |
|---------|------|-------------|
| **Stalled Deal Detection** | Deterministic | No activity >14 days or missing next step |
| **Churn Risk Watchlist** | Deterministic | Renewal <60 days + high tickets or delayed onboarding |
| **Pipeline Summary KPIs** | Deterministic | Total deals, value, avg size, stage breakdown |
| **Action Item Extraction** | Hybrid | Regex heuristics + LLM fallback |
| **Ask the Agent (Q&A)** | LLM | Natural-language questions answered with evidence |
| **Email Drafter** | LLM | AI-generated follow-up emails grounded in data |
| **Semantic Search** | LLM | FAISS vector search using Gemini embeddings |

## 🏗️ Architecture

```
Streamlit Dashboard
        │
   FastAPI Backend
    ┌────┼────┐
    │    │    │
Ingestion  Deterministic  LLM Orchestrator
Engine     Rules (Tools)   (Gemini 2.5 Flash)
    │    │    │
    └────┼────┘
    SQLite + FAISS
```

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, Pydantic v2
- **Frontend:** Streamlit
- **Database:** SQLite (SQLAlchemy 2.0) + FAISS
- **LLM:** Google Gemini 2.5 Flash (text) + text-embedding-004 (vectors)
- **Data:** Pandas, csv module

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/founders-office-ai-ops.git
cd founders-office-ai-ops

# 2. Install dependencies (no torch — lightweight!)
pip install -r requirements.txt

# 3. Configure your API key
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 4. Seed the database with sample data
python seed_data.py

# 5. Verify setup
python check_setup.py

# 6. Start the API server
uvicorn app.main:app --reload --port 8000

# 7. Start the dashboard (new terminal)
streamlit run frontend/dashboard.py
```

## 📊 Seed Data

The included `seed_data.py` generates:
- **20 CRM deals** (including 3 stalled deals & 2 churn risks)
- **5 meeting notes** (Markdown with action items & objections)
- **5 call transcripts** (JSON with realistic sales dialogues)

## 🔑 Business Rules

| Rule | Condition | Output |
|------|-----------|--------|
| Stalled Deal | `last_activity > 14 days` OR `next_step = NULL` | Pipeline Blocker |
| Churn Risk | `renewal < 60 days` AND (`tickets > 5` OR `onboarding = delayed`) | Churn Alert |
| Missing Data | `stage = closing` AND `next_step = NULL` | Data Quality Flag |

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ingest/upload` | Upload CSV/MD/JSON files |
| `POST` | `/api/v1/ingest/build-index` | Build FAISS vector index |
| `GET` | `/api/v1/pipeline/summary` | Pipeline KPIs |
| `GET` | `/api/v1/pipeline/blockers` | Stalled deals |
| `GET` | `/api/v1/churn/watchlist` | Churn risks |
| `POST` | `/api/v1/ask` | Natural-language Q&A |
| `POST` | `/api/v1/email/draft` | AI email drafting |

## 📄 License

MIT

---

*Built as an MVP for startup operations intelligence.*
