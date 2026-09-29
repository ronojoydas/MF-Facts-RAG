"""Project paths and constants. Does not load models or call APIs."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHUNKS_DIR = DATA_DIR / "chunks"

CHROMA_PERSIST_DIR = PROCESSED_DIR / "chroma_db"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_COLLECTION_NAME = "hdfc_mf_facts"
RETRIEVAL_K = 5
MAX_ANSWER_SENTENCES = 3

SUPPORTED_SCHEMES = (
    "HDFC Large Cap Fund",
    "HDFC Flexi Cap Fund",
    "HDFC ELSS Tax Saver Fund",
    "HDFC Small Cap Fund",
    "HDFC Balanced Advantage Fund",
)

PREFERRED_PUBLISHERS = ("HDFC AMC", "SEBI", "AMFI")


if __name__ == "__main__":
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("RAW_DIR:", RAW_DIR)
    print("PROCESSED_DIR:", PROCESSED_DIR)
    print("CHUNKS_DIR:", CHUNKS_DIR)
    print("EMBEDDING_MODEL_NAME:", EMBEDDING_MODEL_NAME)
    print("CHROMA_COLLECTION_NAME:", CHROMA_COLLECTION_NAME)
    print("RETRIEVAL_K:", RETRIEVAL_K)
    print("MAX_ANSWER_SENTENCES:", MAX_ANSWER_SENTENCES)
