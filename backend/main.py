"""NyayAI backend — retrieval-first, grounded, citation-or-refusal.

Endpoints:
  GET  /health   -> corpus stats + key configuration
  GET  /search?q -> BM25-lite top-k over the curated corpus
  POST /ask      -> grounded answer with [S#] citations, or a refusal
"""

import json
import math
import os
import re
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent.parent
CORPUS = json.loads((BASE / "data" / "corpus.json").read_text(encoding="utf-8"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# Retrieval tuning (SCOPE.md Day-2: set once after reading real scores)
K1, B, TOP_K = 1.5, 0.75, 3
SCORE_FLOOR = 0.5  # best-score below this -> refuse, do not hallucinate

app = FastAPI(title="NyayAI", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

TOKEN = re.compile(r"[a-z0-9]+")

# --- BM25-lite (pure stdlib, inspectable, honest) ---------------------------

_docs = [
    {**doc, "_terms": TOKEN.findall(doc["text"].lower()) + TOKEN.findall(doc["title"].lower())}
    for doc in CORPUS
]
_avg_len = sum(len(d["_terms"]) for d in _docs) / max(len(_docs), 1)
_df = {}
for d in _docs:
    for term in set(d["_terms"]):
        _df[term] = _df.get(term, 0) + 1


def bm25(query: str):
    terms = TOKEN.findall(query.lower())
    scores = []
    for d in _docs:
        score = 0.0
        for term in terms:
            tf = d["_terms"].count(term)
            if not tf:
                continue
            idf = math.log((len(_docs) - _df[term] + 0.5) / (_df[term] + 0.5) + 1)
            score += idf * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * len(d["_terms"]) / _avg_len))
        scores.append((score, d))
    scores.sort(key=lambda x: -x[0])
    return [(s, d) for s, d in scores if s > 0][:TOP_K]


# --- API ---------------------------------------------------------------------


class AskBody(BaseModel):
    question: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "corpus": len(CORPUS),
        "gemini_configured": bool(GEMINI_API_KEY),
    }


@app.get("/search")
def search(q: str):
    return {
        "results": [
            {"score": round(score, 3), "id": d["id"], "title": d["title"], "citation": d["citation"], "source": d["source"]}
            for score, d in bm25(q)
        ]
    }


@app.post("/ask")
def ask(body: AskBody):
    hits = bm25(body.question)
    if not hits or hits[0][0] < SCORE_FLOOR:
        raise HTTPException(
            status_code=404,
            detail="No grounded source matched this question — refusing to answer without citations.",
        )
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured in the environment.")

    context = "\n\n".join(
        f"[{d['id']}] ({d['citation']}, {d['source']}) {d['title']}: {d['text']}" for _, d in hits
    )
    prompt = (
        "You are a legal-information assistant. Answer ONLY from the context below. "
        "Cite sources inline as [S#]. If the context does not answer the question, say so plainly. "
        "This is information, not legal advice.\n\n"
        f"Context:\n{context}\n\nQuestion: {body.question}"
    )

    try:
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except (httpx.HTTPError, KeyError, IndexError) as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    cited = {d["id"]: {"title": d["title"], "citation": d["citation"], "source": d["source"]} for _, d in hits}
    return {"answer": answer, "citations": cited, "scores": [{"id": d["id"], "score": round(s, 3)} for s, d in hits]}


# --- static web shell --------------------------------------------------------

app.mount("/web", StaticFiles(directory=BASE / "web", html=True), name="web")


@app.get("/")
def index():
    return FileResponse(BASE / "web" / "index.html")
