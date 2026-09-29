# Architecture — Facts-Only Mutual Fund FAQ Assistant

This document explains the **RAG (Retrieval-Augmented Generation)** design in beginner-friendly language.

**RAG in one sentence:** we do **not** let the LLM invent mutual fund facts. We **look up** official text first, then ask the LLM to **summarize only that text**.

---

## Simple pipeline diagram

```
Official sources (HDFC AMC / SEBI / AMFI)
  ↓
Load (download or copy pages/PDFs)
  ↓
Raw document storage (local files + metadata)
  ↓
Text extraction
  ↓
Chunk (split into small passages)
  ↓
Embed (sentence-transformers/all-MiniLM-L6-v2)
  ↓
ChromaDB (vector database)
  ↓
User question (Streamlit)
  ↓
Question embedding (same MiniLM model)
  ↓
Retrieve relevant chunks (similarity search)
  ↓
Guardrails (advice? PII? too little evidence?)
  ↓
Groq LLM (facts-only system prompt + chunks)
  ↓
Answer + one source link + "Last updated from sources:"
```

There are **two times** this pipeline runs:

1. **Ingestion (once, or when you refresh sources):** sources → load → store raw → extract → chunk → embed → ChromaDB  
2. **Question answering (every chat message):** question → embed → retrieve → guardrails → Groq → UI

---

## 1. Official source documents

**What:** Public pages and PDFs from **HDFC AMC**, **SEBI**, and **AMFI** about the five schemes and related investor processes (for example, how to get a capital-gains statement).

**Why needed:** The problem statement forbids blogs. Official issuers are the **ground truth**. If a number is not in these files, the bot must say it does not know.

**Milestone practice:** keep a **short curated list** of URLs/files (not a giant crawler). Each item has a publisher, a URL, and a recorded date.

---

## 2. Data loading

**What:** A small Python step that reads the curated list and fetches or copies each document into the project.

**Why needed:** The rest of the pipeline should work from **files on disk**, so you can rebuild the index without re-searching the web every time, and you can show evaluators **exactly** what was ingested.

**Beginner note:** loading is “get the file.” It is not yet “understand the file.”

---

## 3. Raw document storage

**What:** A folder such as `data/raw/` holding:

- Original HTML or PDF
- A sidecar metadata file (scheme names, URL, publisher, fetch date)

**Why needed:**

- Debugging (“what did we actually download?”)
- Re-running chunking without downloading again
- Filling **“Last updated from sources:”** from metadata, not from the LLM’s memory

Raw storage is **not** the vector database. It is the **original evidence**.

---

## 4. Text extraction

**What:** Convert PDF/HTML into **plain text** (and maybe a title). Strip menus, ads, and junk so chunks are mostly real content.

**Why needed:** Embedding models and the LLM work on **text**. A PDF is not usable until words are extracted. Bad extraction → wrong answers.

---

## 5. Chunking

**What:** Split long documents into **overlapping passages** (for example a few hundred tokens/characters each) so each piece is small enough to embed and to paste into a prompt.

**Why needed:**

- MiniLM has a **length limit**. A whole SID PDF cannot go in as one vector.
- Retrieval should return the **paragraph about exit load**, not the entire 80-page document.
- Overlap (a little repeated text at chunk edges) reduces the chance that a sentence is cut in half.

Each chunk should keep **metadata**: source URL, scheme, date, publisher. That metadata is how we **cite** later.

---

## 6. Embedding with `sentence-transformers/all-MiniLM-L6-v2`

**What:** Turn each chunk into a list of numbers (a **vector**) that represents meaning. The same model later turns the **user question** into a vector.

**Why this model:** It is specified for the milestone. It is small, runs on a laptop, and is good enough for English FAQ retrieval.

**Why embeddings exist:** Computers cannot “search by meaning” with only keyword match. Two sentences that mean the same thing can sit **close together** in vector space even if they use different words (“exit load” vs “redemption fee if you sell early”).

**Important:** Use the **same** model for documents and questions. Mixing models breaks similarity.

---

## 7. ChromaDB vector database

**What:** A local database that stores:

- The embedding vector
- The chunk text
- Metadata (URL, scheme, date)

At query time it finds the **nearest neighbors** of the question vector.

**Why needed:** Without a vector store you would scan every chunk by hand. ChromaDB is the milestone’s required store and is simple for a class project (often a folder on disk, no separate server required).

---

## 8. User question

**What:** Text typed in **Streamlit**.

**Why needed:** This is the only product surface for the milestone. The UI should not ask for PAN, Aadhaar, bank details, OTP, email, or phone.

---

## 9. Question embedding

**What:** Run the **same MiniLM model** on the user’s question to get one vector.

**Why needed:** Retrieval is “find document vectors close to this question vector.” If you skip this step, ChromaDB has nothing to compare.

---

## 10. Similarity retrieval

**What:** Ask ChromaDB for the **top-k** chunks (small k, e.g. 3–5) whose vectors are most similar to the question.

**Why needed:** The LLM should see **only the relevant paragraphs**, not the whole corpus. That keeps answers grounded and prompts short.

**Risk:** If the question is vague, the nearest chunks might be the **wrong scheme**. Later code should prefer chunks whose metadata matches a detected scheme name, or ask the user to name the fund.

---

## 11. Guardrails

**What:** Rules that run **before** Groq (and sometimes after, as a check):

| Guardrail | If it fires |
|-----------|-------------|
| Looks like **investment advice** (buy/sell/recommend/best fund/predict returns) | Polite refusal; **do not** retrieve-and-advise |
| Looks like **PII** (PAN, Aadhaar, account, OTP, email, phone) | Privacy refusal; **do not store** the message |
| **No useful chunks** (empty index, very low similarity) | “I don’t know” |
| Question about a **fund we do not cover** | Out-of-scope message |
| Retrieved text still **doesn’t contain** the asked fact | Instruct Groq to say “I don’t know”; do not invent |

**Why needed:** RAG without guardrails can still **recommend funds** or **leak** that the user typed a PAN into logs. Safety and privacy are product requirements, not extras.

Guardrails are **code and prompts**, not a separate paid product.

---

## 12. Groq LLM

**What:** A hosted large language model API. We send:

- A **system prompt**: facts only, ≤ 3 sentences, cite one URL from the chunks, never advise, say “I don’t know” if the chunks lack the fact
- The **user question**
- The **retrieved chunk texts** plus their URLs and dates

**Why needed:** Users want a **readable sentence**, not a dump of SID paragraphs. Groq is the required LLM for this milestone.

**Why Groq is not enough alone:** Without retrieved chunks, the model would guess expense ratios. **Retrieval is the source of truth; Groq is the writer.**

---

## 13. Answer generation

**What:** Groq returns short text. Our app **formats** it:

- Body: at most three sentences
- One **source link** taken from chunk metadata (not a URL the model invented)
- `Last updated from sources:` from metadata dates

**Why needed:** Evaluators can check **grounding**. If the model outputs a URL that was not in metadata, the app should **replace** it with the retrieved chunk’s URL.

---

## 14. Source citation

**What:** One official link per factual answer, plus the last-updated line.

**Why needed:** Trust. The user (and the mentor) can open the same page we ingested.

**Rule:** Citation comes from **our metadata**, not from the model’s imagination.

---

## 15. Streamlit UI

**What:** A simple web page run locally:

- Title: facts-only HDFC FAQ (not an advisor)
- Text box + send
- Chat history **in the session only** (no PII logging)
- Display of answer, link, and last-updated line
- Short disclaimer: not investment advice

**Why needed:** It is the required UI. Mentors can click through without using the terminal.

---

## How the pieces depend on each other

```
                    ┌─────────────────────────┐
                    │   data/raw + metadata   │
                    └───────────┬─────────────┘
                                │ extract + chunk
                                ▼
                    ┌─────────────────────────┐
                    │ MiniLM embeddings       │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
   Streamlit ──► question ──► MiniLM ──► ChromaDB search
                    │                           │
                    │         top chunks        │
                    ▼                           ▼
              Guardrails ◄──────────────────────┘
                    │ pass
                    ▼
                  Groq
                    │
                    ▼
         Answer + URL + last updated
                    │
                    ▼
                Streamlit
```

If **ChromaDB is empty**, retrieval fails → guardrail → “I don’t know.”  
If **guardrails fail**, Groq is **not** asked to invent a portfolio.  
If **Groq is down**, the UI should show an error, not a fake ratio.

---

## What we are not building in this architecture

- A recommendation engine
- A cloud multi-tenant database of users
- Fine-tuned finance models
- Scraping unofficial blogs

This keeps the milestone **small, explainable, and safe**.
