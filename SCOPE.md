# SCOPE — the weekend MVP box

**One weekend. One working loop. Nothing bigger.**

## In the box (v0)

| Piece | Contract |
|---|---|
| `/search?q=` | BM25-lite (pure stdlib) over `data/corpus.json`, top-3 with scores |
| `/ask` | retrieve top-3 → Gemini generateContent grounded **only** on them → answer + `[S#]` citations; **refuses** when no snippet scores above the floor |
| `/health` | corpus count + whether `GEMINI_API_KEY` is configured |
| Voice | WebSpeech mic-in (feature-guarded), speechSynthesis speak-out — browser only, zero backend |
| Corpus seed | 6 real snippets w/ exact source names; citation = `{source, citation}` |

## Explicitly out (do not drift)

- PDF/OCR ingestion, full-index crawling, login/accounts, payment anything.
- Vector DBs / embeddings — the BM25-lite ranker is the honest v0; swap later if recall demands it.
- Legal advice tone — every surface repeats "information, NOT legal advice".

## Day-2 checklist (first hour of the weekend)

1. Validate corpus text against official sources (constitutionofindia.nic.in / India Code) — fix wording, keep citations exact.
2. Pick the response threshold by reading `/search` scores for 10 real questions; set `SCORE_FLOOR` once, in code, with a comment.
3. Only then touch the LLM prompt.
