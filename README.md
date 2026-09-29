# Facts-Only MF Assistant

A retrieval-augmented generation (RAG) chatbot for factual information about selected HDFC Mutual Fund schemes. It retrieves information from official source documents and provides a concise answer with source attribution.

**Supported AMC:** HDFC Mutual Fund

**Supported schemes:**

- HDFC Large Cap Fund
- HDFC Flexi Cap Fund
- HDFC ELSS - Tax Saver Fund
- HDFC Small Cap Fund
- HDFC Balanced Advantage Fund

The assistant answers factual questions only. It uses official HDFC Mutual Fund, SEBI, and AMFI sources, provides source links, and displays `Last updated from sources:` when a source date is available. It refuses investment advice and recommendations, return predictions and calculations, questions about unsupported schemes, and requests involving sensitive personal information.

## Architecture

```text
Official sources
→ extraction
→ semantic chunks
→ sentence-transformers/all-MiniLM-L6-v2
→ ChromaDB
→ semantic retrieval + reranking
→ deterministic guardrails
→ Groq
→ Streamlit
```

## Project statistics

- 15 source entries
- 213 corpus chunks
- 213 ChromaDB vectors
- 5 supported schemes

## Prerequisites

- Python 3.x
- A Groq API key
- Internet access for the initial embedding-model download

## Windows setup

Run these commands from the project root:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Configure the Groq API key

Create a file named `.env` in the project root with:

```dotenv
GROQ_API_KEY=your_key_here
```

Never commit `.env` or share your API key. `.env` is already excluded by `.gitignore`. The committed `.env.example` is a placeholder and should not contain a real key.

## Prepare the embedding model and vector store

The application uses `sentence-transformers/all-MiniLM-L6-v2`. The model must be downloaded and cached before the app can answer factual questions. The app loads the cached model locally, while the preparation command below downloads it on first use if needed.

The persistent ChromaDB store is `data/processed/chroma_db/`. That local database is not committed. From the project root, build it from `data/processed/chunks.jsonl` and cache the model by running:

```powershell
python -m src.retrieval.embed_and_store
```

This script rebuilds the dedicated ChromaDB directory before indexing the corpus. Run it when preparing a fresh clone or intentionally rebuilding the index; it replaces the existing local vector store.

## Run the application

From the project root, with the environment activated and the model/vector store prepared:

```powershell
streamlit run app.py
```

## Example questions

- What is the benchmark of HDFC ELSS - Tax Saver Fund?
- What is the investment objective of HDFC Large Cap Fund?
- What is the minimum purchase amount for HDFC ELSS - Tax Saver Fund?

## Limitations

- Facts-only; answers depend on the official source context available to the system.
- Limited to the five supported schemes listed above.
- No investment advice, recommendations, or personalized financial guidance.
- No return predictions or personalized return calculations.
- Uses public official sources only.
- Source metadata and update dates depend on the available official source documents.

## Project structure

```text
.
├── app.py                         # Streamlit application
├── src/
│   ├── config.py                  # Project paths and model/collection settings
│   ├── guardrails.py              # Deterministic question classification
│   ├── generation.py              # Grounded Groq answer generation
│   ├── retrieval/
│   │   ├── rerank.py              # Semantic retrieval and reranking
│   │   └── embed_and_store.py     # Model setup and ChromaDB indexing
│   └── ingestion/                 # Source extraction, chunking, and verification
├── data/
│   ├── sources/sources.csv        # Source registry
│   ├── raw/                       # Original source PDFs
│   ├── chunks/                    # Clean extracted text documents
│   └── processed/
│       └── chunks.jsonl           # 213-chunk corpus
├── docs/                          # PRD, architecture, and implementation phases
├── requirements.txt
├── .env.example
└── .gitignore
```

`data/processed/chroma_db/` is generated locally by the preparation command and is excluded from Git.
