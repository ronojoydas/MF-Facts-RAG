# Implementation plan and current status

The six implementation phases below are complete. This document retains the original phase structure and records the implementation that currently exists in the repository. The actual module paths are listed below; early planning filenames may differ from the final filenames.

## Current implementation

- **Project configuration:** `src/config.py` defines project paths, `sentence-transformers/all-MiniLM-L6-v2`, the persistent ChromaDB path, and collection name.
- **Corpus preparation:** source records live in `data/sources/sources.csv`; original PDFs are in `data/raw/`; clean scheme text is in `data/chunks/`; `src/ingestion/` contains extraction, chunking, and verification scripts. The corpus is `data/processed/chunks.jsonl` (213 chunks across five supported schemes).
- **Vector store:** `src/retrieval/embed_and_store.py` builds the `hdfc_mf_facts` collection in `data/processed/chroma_db/`. The current local collection contains 213 vectors and is excluded from Git.
- **Retrieval:** `src/retrieval/rerank.py` performs semantic candidate retrieval and lightweight relevance reranking.
- **Guardrails and answers:** `src/guardrails.py` deterministically blocks advice, sensitive personal information, return predictions, unsupported schemes, and unrelated questions. `src/generation.py` uses Groq to produce concise answers grounded in supplied official context.
- **Application:** `app.py` connects guardrails, retrieval, and answer generation in the Streamlit interface.
- **Secrets and dependencies:** configure `GROQ_API_KEY` in a local `.env`; `.env` is ignored by Git. Runtime dependencies are listed in `requirements.txt`.

For a fresh checkout, install `requirements.txt`, create `.env`, then run `python -m src.retrieval.embed_and_store` from the repository root. That command downloads/caches the embedding model if needed and rebuilds the local vector store from `data/processed/chunks.jsonl`. Start the UI with `streamlit run app.py`.

---

## Phase 1 — Project Setup [COMPLETE]

The repository contains the project configuration, dependency list, environment template, ignore rules, documentation, and expected data/source directories. `src/config.py` holds the actual paths, embedding model, and collection settings. The actual runtime application is implemented; this is no longer an empty skeleton.

## Phase 2 — Loading and Chunking [COMPLETE]

The source registry contains 15 source entries. PDFs and clean extracted scheme text are present under `data/raw/` and `data/chunks/`. Ingestion utilities under `src/ingestion/` extract and prepare semantic chunks; `src/ingestion/chunk_documents.py` writes the verified 213-record corpus to `data/processed/chunks.jsonl` with source metadata.

## Phase 3 — Embedding and Vector Database [COMPLETE]

The project uses `sentence-transformers/all-MiniLM-L6-v2` and a persistent ChromaDB collection named `hdfc_mf_facts` at `data/processed/chroma_db/`. `src/retrieval/embed_and_store.py` reads the JSONL corpus, embeds its chunks, and builds the collection. The verified local database currently contains 213 vectors. The database directory is generated and ignored by Git, so a fresh clone must run:

```powershell
python -m src.retrieval.embed_and_store
```

The script clears and rebuilds this dedicated local database directory.

## Phase 4 — Guardrails [COMPLETE]

`src/guardrails.py` provides deterministic classification before retrieval or generation. It permits supported factual questions and blocks investment advice/recommendations, sensitive personal/account information, expected or predicted returns, unsupported schemes, and unrelated questions. Guardrail tests are in `src/test_guardrails.py`.

## Phase 5 — Retrieval and LLM Answer [COMPLETE]

`src/retrieval/rerank.py` retrieves semantic candidates from ChromaDB and reranks them with generic lexical and field/heading relevance. `src/generation.py` calls Groq only after the application has classified the question and supplied retrieved context. Answers are limited to available context, with official source URL and source update metadata when available. Retrieval and generation test scripts are located under `src/retrieval/` and `src/`.

## Phase 6 — User Interface [COMPLETE]

`app.py` is the Streamlit chat interface. It runs deterministic guardrails first, then uses the existing retrieval and generation modules for allowed questions. It displays concise answers, clickable source links, available update dates, and refusal messages. Run it from the project root with:

```powershell
streamlit run app.py
```

## Phase order

| Order | Phase | Status |
|-------|-------|--------|
| 1 | Project Setup | Complete |
| 2 | Loading and Chunking | Complete |
| 3 | Embedding and Vector Database | Complete |
| 4 | Guardrails | Complete |
| 5 | Retrieval and LLM Answer | Complete |
| 6 | User Interface | Complete |

Deployment, hosted infrastructure, and user accounts are outside the current local application implementation.
