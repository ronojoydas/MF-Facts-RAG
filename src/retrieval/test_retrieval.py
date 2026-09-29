"""Inspect top-k ChromaDB matches for sample questions; does not generate answers."""

import argparse
import sys

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL_NAME,
)
from src.retrieval.rerank import retrieve as retrieve_reranked


TEST_QUESTIONS = [
    "What is the minimum purchase amount for HDFC ELSS - Tax Saver Fund?",
    "What is the benchmark of HDFC ELSS - Tax Saver Fund?",
    "What is the investment objective of HDFC Large Cap Fund?",
    "What is the investment objective of HDFC Small Cap Fund?",
    "What is the investment objective of HDFC Balanced Advantage Fund?",
    "What is the investment objective of HDFC Flexi Cap Fund?",
]
TOP_K = 3
CANDIDATE_K = 32


def print_results(question, candidate_count, ranked_results):
    print(f"\nQUESTION: {question}")
    print(f"Semantic candidates: {candidate_count}")
    if not ranked_results:
        print("No results returned.")
        return

    for index, result in enumerate(ranked_results):
        print(f"\nRank: {index + 1}")
        print(f"Scheme: {result.scheme}")
        print(f"Chunk ID: {result.chunk_id}")
        print(f"Rerank score: {result.score:.4f}")
        print(f"Score components: {result.components}")
        print(f"Semantic distance: {result.distance:.4f}")
        print(f"Source ID: {result.source_id}")
        print(f"Source URL: {result.source_url}")
        print("Retrieved text:")
        print(result.document)


def main():
    # Retrieved source text can contain rupee signs and other non-CP1252 glyphs.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "question",
        nargs="*",
        help="Optional question to run instead of the six built-in sample questions.",
    )
    args = parser.parse_args()
    questions = [" ".join(args.question)] if args.question else TEST_QUESTIONS

    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print(f"Collection: {collection.name}")
    print(f"Embedding model: {EMBEDDING_MODEL_NAME}")
    print(f"Questions to run: {len(questions)}")
    for question in questions:
        candidates, ranked = retrieve_reranked(
            question, model, collection, candidate_k=CANDIDATE_K, top_k=TOP_K
        )
        candidate_count = len(candidates.get("ids", [[]])[0])
        print_results(question, candidate_count, ranked)


if __name__ == "__main__":
    main()
