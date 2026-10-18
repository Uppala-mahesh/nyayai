# NyayAI — legal information, minus the jargon

An AI-assisted platform that makes **Indian legal information approachable** —
retrieval-first answers with citations you can open, plus voice in/out.

> **Information, NOT legal advice.** Every answer must trace to a source.

- **Retrieval-first**: a hand-curated corpus (`data/corpus.json`) scored by a stdlib BM25-lite ranker — no black-box vectors, everything inspectable.
- **Grounded answers**: the LLM may answer **only** from retrieved snippets and must cite them; with no hits, it refuses.
- **Voice**: browser WebSpeech for mic input, speechSynthesis for playback — zero infra cost.

## Status

Weekend MVP build (see `SCOPE.md` for the locked box). Scaffold committed; pipeline lands on the weekend sprint.

## Run (dev)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
set GEMINI_API_KEY=...          # from AI Studio — never commit it
uvicorn backend.main:app --reload
# open http://localhost:8000
```

## Test

```bash
curl "http://localhost:8000/health"
curl "http://localhost:8000/search?q=identity%20theft"
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"question\":\"What does Article 21 protect?\"}"
```
