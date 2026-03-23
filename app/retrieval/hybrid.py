"""
Hybrid Retrieval Service – combines SQL queries with FAISS vector search.

Embeddings are generated via the NEW google-genai SDK (v1.0+) using
model gemini-embedding-001 — NO local torch/sentence-transformers needed.

• SQL layer  → structured metrics from the `deals`, `meeting_notes`, `transcripts` tables.
• FAISS layer → semantic similarity search over ingested text chunks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Deal, MeetingNoteRecord, TranscriptRecord

logger = logging.getLogger(__name__)

# ── Module-level state ─────────────────────────────────────
_client = None
_faiss = None
_index = None
_doc_store: list[dict] = []  # parallel list: {id, text, source, account}

EMBEDDING_MODEL = "gemini-embedding-001"


def _load_faiss():
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss


_embed_client = None


def _get_embed_client():
    """Lazy-init a google.genai.Client for embedding calls."""
    global _embed_client
    if _embed_client is None:
        from google import genai
        _embed_client = genai.Client(
            api_key=settings.google_api_key,
        )
    return _embed_client


def _get_embedding(text: str) -> np.ndarray:
    """Embed a single text string via Gemini API."""
    client = _get_embed_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    vec = result.embeddings[0].values
    return np.array([vec], dtype="float32")


def _get_embeddings_batch(texts: list[str]) -> np.ndarray:
    """Embed a batch of texts via Gemini API."""
    client = _get_embed_client()
    all_vecs = []
    # Process in batches of 20 to avoid API limits
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        for text in batch:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
            )
            all_vecs.append(result.embeddings[0].values)
    return np.array(all_vecs, dtype="float32")


# ── Index management ───────────────────────────────────────

def build_index(db: Session) -> int:
    """
    (Re-)build the FAISS index from all meeting notes and transcripts
    currently stored in SQLite.  Returns the total document count.
    """
    global _index, _doc_store
    _load_faiss()

    chunks: list[dict] = []

    # Meeting notes
    for note in db.query(MeetingNoteRecord).all():
        chunks.append({
            "id": note.note_id,
            "text": note.content,
            "source": note.source_file,
            "account": note.account_name,
        })

    # Transcripts
    for t in db.query(TranscriptRecord).all():
        chunks.append({
            "id": t.transcript_id,
            "text": t.full_text,
            "source": t.source_file,
            "account": t.account_name,
        })

    if not chunks:
        logger.warning("No documents to index")
        _doc_store = []
        _index = None
        return 0

    texts = [c["text"] for c in chunks]
    embeddings = _get_embeddings_batch(texts)

    # Normalize for cosine similarity via inner product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    dim = embeddings.shape[1]
    _index = _faiss.IndexFlatIP(dim)
    _index.add(embeddings)
    _doc_store = chunks

    # Persist to disk
    idx_path = Path(settings.faiss_index_path)
    idx_path.mkdir(parents=True, exist_ok=True)
    _faiss.write_index(_index, str(idx_path / "index.faiss"))

    logger.info("FAISS index built with %d documents (dim=%d)", len(chunks), dim)
    return len(chunks)


def search_similar(query: str, top_k: int = 5) -> list[dict]:
    """
    Semantic search over the FAISS index.
    Returns a list of dicts with keys: id, text, source, account, score.
    """
    if _index is None or not _doc_store:
        return []

    q_vec = _get_embedding(query)
    norm = np.linalg.norm(q_vec)
    if norm > 0:
        q_vec = q_vec / norm

    scores, indices = _index.search(q_vec, min(top_k, len(_doc_store)))

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        doc = _doc_store[idx].copy()
        doc["score"] = float(score)
        results.append(doc)
    return results


# ── SQL helpers ────────────────────────────────────────────

def sql_search_deals(db: Session, account_name: Optional[str] = None) -> list[Deal]:
    q = db.query(Deal)
    if account_name:
        q = q.filter(Deal.account_name.ilike(f"%{account_name}%"))
    return q.all()


def sql_search_notes(db: Session, account_name: Optional[str] = None) -> list[MeetingNoteRecord]:
    q = db.query(MeetingNoteRecord)
    if account_name:
        q = q.filter(MeetingNoteRecord.account_name.ilike(f"%{account_name}%"))
    return q.order_by(MeetingNoteRecord.date.desc()).all()


# ── Hybrid query ───────────────────────────────────────────

class HybridRetriever:
    """Combines SQL-based structured retrieval with FAISS semantic search."""

    def __init__(self, db: Session):
        self.db = db

    def query(
        self,
        question: str,
        account_name: Optional[str] = None,
        top_k: int = 5,
    ) -> dict:
        deals = sql_search_deals(self.db, account_name)
        notes = sql_search_notes(self.db, account_name)
        semantic = search_similar(question, top_k=top_k)

        return {
            "deals": [
                {
                    "deal_id": d.deal_id,
                    "account_name": d.account_name,
                    "stage": d.stage,
                    "value": d.deal_value,
                    "next_step": d.next_step,
                    "last_activity": str(d.last_activity_date) if d.last_activity_date else None,
                }
                for d in deals
            ],
            "notes": [
                {
                    "note_id": n.note_id,
                    "account_name": n.account_name,
                    "date": str(n.date),
                    "snippet": n.content[:500],
                    "source": n.source_file,
                }
                for n in notes[:top_k]
            ],
            "semantic_matches": semantic,
        }
