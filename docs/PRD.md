# Product Requirements Document

**Product:** Facts-Only Mutual Fund FAQ Assistant  
**Platform context:** Groww (class milestone product)  
**AMC covered:** HDFC Mutual Fund  
**Audience of this document:** NextLeap milestone, beginner-friendly scope  
**Status:** Planning only — no application code yet

---

## 1. Project goal

Build a small **Retrieval-Augmented Generation (RAG)** chatbot that answers **factual questions only** about **five selected HDFC mutual fund schemes**, using **verified public sources**.

The assistant must:

- Give short, citation-backed facts
- Never give investment advice
- Say “I don’t know” when the sources do not contain the answer

This is a class milestone, not a full Groww product. The goal is to demonstrate a working, safe RAG pipeline with a simple Streamlit UI.

---

## 2. Problem being solved

Investors often ask simple factual questions (expense ratio, exit load, SIP minimum, lock-in, riskometer, benchmark, how to download a capital-gains statement). Answers on the internet mix official facts with blogs, opinions, and sales language.

This project solves a narrow problem:

**Give a beginner a trustworthy, source-linked factual answer for a small set of HDFC schemes — without turning into an advisor.**

---

## 3. Target users

| User | How they use it |
|------|-----------------|
| NextLeap evaluators / mentors | Check that RAG, guardrails, citations, and refusal of advice work |
| Beginner self-learners | Ask scheme facts they could also look up on HDFC AMC / SEBI / AMFI |
| Groww-style retail investor (simulated) | Same factual FAQ use case, not personalized advice |

**Not a target user for this milestone:** distributors, relationship managers, or anyone expecting portfolio recommendations.

---

## 4. Product scope

### In scope

- **Five schemes only:**
  1. HDFC Large Cap Fund
  2. HDFC Flexi Cap Fund
  3. HDFC ELSS Tax Saver Fund
  4. HDFC Small Cap Fund
  5. HDFC Balanced Advantage Fund
- Public **official** documents and pages from **HDFC AMC**, **SEBI**, and **AMFI**
- A **local RAG pipeline:** load → chunk → embed (`sentence-transformers/all-MiniLM-L6-v2`) → store in **ChromaDB**
- **Question-time retrieval**, **guardrails**, **Groq LLM**, **source citation**
- A simple **Streamlit** chat UI
- Privacy: no collection of identity or financial identifiers
- Facts-only answers, max **three sentences**, plus a source link and a “Last updated from sources:” line

### Out of scope

- Recommending a fund, buy/sell, portfolio construction, or “what should I do?”
- Predicting or comparing **returns** / performance as advice
- Making investment decisions for the user
- Third-party blogs, YouTube, news sites, or unofficial aggregators as factual sources
- User accounts, login, conversation history stored with PII
- Live Groww production integration, payments, KYC, or order placement
- Covering all HDFC schemes or other AMCs
- Multi-language UI, mobile apps, or a production-grade crawler
- Fine-tuning custom embedding or LLM models
- Real-time NAV / market data feeds (unless a chosen official page happens to include a snapshot we ingested)

---

## 5. In-scope features

1. **Ingest a small, curated set of official pages/PDFs** into a local store.
2. **Chunk and embed** text with `all-MiniLM-L6-v2`.
3. **Store vectors in ChromaDB** with metadata (scheme name, source URL, retrieved date).
4. **Accept a user question** in Streamlit.
5. **Retrieve the most similar chunks** for that question.
6. **Guardrails** before calling the LLM:
   - Block / refuse investment-advice intent
   - Block questions that look like they contain PAN, Aadhaar, bank numbers, OTPs, emails, phones
   - If retrieval is empty or too weak, answer “I don’t know”
7. **Groq** generates a concise factual answer **only from retrieved text**.
8. **Every factual answer** includes:
   - Direct answer
   - One clear source link
   - Line: `Last updated from sources:` (date we recorded when ingesting or last refresh)
9. **Polite refusal** for advice and for out-of-scope schemes/topics.

---

## 6. Out-of-scope features

- Fund recommendation engines
- Risk profiling questionnaires used to suggest products
- SIP calculators that imply “you should invest X”
- Comparison tables ranked by “best returns”
- Storing chat logs that include personal data
- Scraping the whole internet
- Admin dashboards, analytics, A/B testing

---

## 7. Supported factual questions

The assistant **should try** to answer questions of this type **when the ingested sources contain the fact**:

| Topic | Example |
|-------|---------|
| Expense ratio | “What is the expense ratio of HDFC Flexi Cap Fund?” |
| Exit load | “What is the exit load of HDFC Large Cap Fund?” |
| Minimum SIP | “What is the minimum SIP for HDFC Small Cap Fund?” |
| ELSS lock-in | “What is the lock-in period for HDFC ELSS Tax Saver Fund?” |
| Riskometer | “What is the riskometer of HDFC Balanced Advantage Fund?” |
| Benchmark | “What is the benchmark of HDFC Large Cap Fund?” |
| Capital-gains statement | “How can I download a capital-gains statement?” (from official investor-service / AMFI / AMC process pages we ingested) |

Questions must name or clearly imply one of the **five schemes** (except process questions like capital-gains download, which may be AMC/Groww-process facts from official docs).

If the user asks about a **different fund**, the assistant should say it only covers these five schemes.

---

## 8. Safety requirements

The assistant **must**:

- Answer **only** using retrieved source material (no invented ratios, loads, or lock-ins)
- Attach **one source link** with every factual answer
- Keep answers **concise** (≤ 3 sentences of body text)
- Say **“I don’t know”** when sources do not contain the answer
- **Refuse investment-advice questions politely** (recommend, buy, sell, “best fund”, “where should I put my money”, return predictions)
- **Not request or store personal information**
- Treat **Groww as the product shell**, not as a license to give personalized financial advice

---

## 9. Privacy requirements

The system **must not accept or store**:

- PAN
- Aadhaar
- Bank account numbers
- OTPs
- Email addresses
- Phone numbers

Implementation intent (for later phases):

- Detect these patterns in the **question** and refuse with a privacy message
- Do not write user questions that contain these into logs, ChromaDB, or files
- Do not ask the user for KYC or account details in the UI copy

---

## 10. Source requirements

- **Public sources only**
- **Preferred:** HDFC AMC, SEBI, AMFI
- **Do not** use third-party blogs as factual sources
- Each ingested document should keep:
  - Canonical **URL** (or official PDF path)
  - **Publisher** (HDFC AMC / SEBI / AMFI)
  - **Date we last fetched or recorded** (for “Last updated from sources:”)
- Scheme-specific facts (expense ratio, exit load, SIP, riskometer, benchmark) should come from **scheme documents / SID / KIM / official scheme pages** where possible
- Process facts (capital-gains statement) should come from **official investor services** pages, not forums

*This milestone will use a **small, manually curated** source list — not an unbounded web crawler.*

---

## 11. Answer requirements

Every **factual** answer should:

1. **Directly answer** the question
2. Use **only** retrieved source information
3. Include **one clear source link**
4. Include the line: **`Last updated from sources:`** followed by the recorded date
5. Be **no more than three sentences** (the source line can sit below those sentences)

**Refusal answers** (advice / privacy / out of scope) do not need a fund fact citation, but should still be polite and short.

---

## 12. Success criteria (milestone)

The project is successful if:

1. A user can open Streamlit and ask a supported factual question about one of the five schemes.
2. The answer is short, grounded in retrieved chunks, and includes a real official URL plus “Last updated from sources:”.
3. Asking “Which HDFC fund should I buy?” is **refused** without a recommendation.
4. Pasting a PAN-like string is **refused** and **not stored**.
5. Asking a fact **not in the corpus** yields **“I don’t know”** rather than a guessed number.
6. The stack matches the brief: **MiniLM embeddings, ChromaDB, Groq, Streamlit**.
7. Scope stays small: five schemes, curated official sources, beginner-maintainable code.

---

## 13. Known limitations

- Facts can go **stale** after documents change; we only know the date we recorded at ingest.
- **Direct plans vs regular plans**, **IDCW vs growth**, and **option-specific** expense ratios may be incomplete if we ingest only one page.
- Embedding similarity can retrieve the **wrong scheme** if questions are vague (“what is the expense ratio?” with no fund name).
- Groq may still **hallucinate** if the prompt is weak; guardrails and “I don’t know” are required, not optional.
- **Capital-gains download** steps may differ between Groww app vs AMC portal; we only answer what official ingested text says.
- This is **not** SEBI-registered advice, **not** a Groww production system, and **not** complete coverage of SID/KIM legal text.
- Local ChromaDB and a Groq API key are **developer-machine** constraints, not a multi-user cloud service.

---

## 14. Technology (for requirements alignment)

| Layer | Choice |
|-------|--------|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | ChromaDB |
| LLM | Groq |
| UI | Streamlit |

These choices are **fixed** for the milestone so evaluation is straightforward.
