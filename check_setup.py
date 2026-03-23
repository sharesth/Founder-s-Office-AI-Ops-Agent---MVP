#!/usr/bin/env python3
"""
Quick smoke-test: verifies your Google API key works for BOTH
text generation (Gemini) and embeddings (text-embedding-004).

Uses the NEW google-genai SDK (v1.0+): `from google import genai`

Run:  python check_setup.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


def check_text_generation():
    """Test Gemini text generation with new SDK."""
    print("=" * 50)
    print("1️⃣  Testing TEXT GENERATION (Gemini)...")
    print("=" * 50)
    try:
        from google import genai
        from google.genai import types
        from app.config import settings

        client = genai.Client(api_key=settings.google_api_key)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents="Reply with exactly one word: WORKING",
            config=types.GenerateContentConfig(
                max_output_tokens=50,
                temperature=0.0,
            ),
        )
        result = response.text.strip()
        print(f"   Model: {settings.gemini_model}")
        print(f"   Response: {result}")
        print("   ✅ Text generation is WORKING\n")
        return True
    except Exception as e:
        print(f"   ❌ Text generation FAILED: {e}\n")
        return False


def check_embeddings():
    """Test Google embeddings with new SDK (text-embedding-004)."""
    print("=" * 50)
    print("2️⃣  Testing EMBEDDINGS (text-embedding-004)...")
    print("=" * 50)
    try:
        from google import genai
        from app.config import settings

        client = genai.Client(
            api_key=settings.google_api_key,
            http_options={"api_version": "v1"},
        )

        result = client.models.embed_content(
            model="text-embedding-004",
            contents="Hello, this is a test",
        )
        vec = result.embeddings[0].values
        print(f"   Model: text-embedding-004")
        print(f"   Vector dimension: {len(vec)}")
        print(f"   First 5 values: {vec[:5]}")
        print("   ✅ Embeddings are WORKING\n")
        return True
    except Exception as e:
        print(f"   ❌ Embeddings FAILED: {e}\n")
        return False


def check_database():
    """Test SQLAlchemy + SQLite setup."""
    print("=" * 50)
    print("3️⃣  Testing DATABASE (SQLAlchemy + SQLite)...")
    print("=" * 50)
    try:
        from app.db.models import init_db, SessionLocal, Deal, MeetingNoteRecord, TranscriptRecord

        init_db()
        db = SessionLocal()
        deal_count = db.query(Deal).count()
        note_count = db.query(MeetingNoteRecord).count()
        transcript_count = db.query(TranscriptRecord).count()
        db.close()
        print(f"   Deals in DB: {deal_count}")
        print(f"   Meeting Notes in DB: {note_count}")
        print(f"   Transcripts in DB: {transcript_count}")
        if deal_count == 0:
            print("   ⚠️  DB is empty — run `python seed_data.py` first!")
            return True  # DB works but is empty
        print("   ✅ Database is WORKING\n")
        return True
    except Exception as e:
        print(f"   ❌ Database FAILED: {e}\n")
        return False


def main():
    print("\n🔍 Founder's Office AI Ops — Setup Checker\n")
    print("   SDK: google-genai (v1.0+)")
    print("   Import: from google import genai\n")

    results = {
        "Text Generation": check_text_generation(),
        "Embeddings": check_embeddings(),
        "Database": check_database(),
    }

    print("=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    all_pass = True
    for name, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"   {name}: {status}")
        if not ok:
            all_pass = False

    print()
    if all_pass:
        print("🎉 All checks passed! You're ready to run the app.")
        print("   → python seed_data.py              (seed the database)")
        print("   → uvicorn app.main:app --reload     (start API)")
        print("   → streamlit run frontend/dashboard.py")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        if not results["Text Generation"] or not results["Embeddings"]:
            print("   Hint: Check your GOOGLE_API_KEY in .env")
            print("   Hint: Run: pip install google-genai")

    print()


if __name__ == "__main__":
    main()
