"""Embed the prepared corpus and upsert it into persistent ChromaDB storage."""

import json
import shutil

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL_NAME,
    PROCESSED_DIR,
)


CORPUS_PATH = PROCESSED_DIR / "chunks.jsonl"
METADATA_FIELDS = (
    "scheme",
    "source_id",
    "source_type",
    "title",
    "source_url",
    "publisher",
    "last_updated",
)
BATCH_SIZE = 32


def load_chunks():
    chunks = []
    seen_ids = set()
    with CORPUS_PATH.open(encoding="utf-8") as corpus_file:
        for line_number, line in enumerate(corpus_file, start=1):
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number}: {error}") from error

            chunk_id = str(chunk.get("chunk_id", "")).strip()
            text = str(chunk.get("text", "")).strip()
            if not chunk_id or not text:
                raise ValueError(f"Line {line_number} needs a non-empty chunk_id and text")
            if chunk_id in seen_ids:
                raise ValueError(f"Duplicate chunk_id in corpus: {chunk_id}")
            missing = [field for field in METADATA_FIELDS if field not in chunk]
            if missing:
                raise ValueError(f"Line {line_number} is missing metadata fields: {missing}")
            seen_ids.add(chunk_id)
            chunks.append(chunk)
    if not chunks:
        raise ValueError(f"No chunks found in {CORPUS_PATH}")
    return chunks


def main():
    chunks = load_chunks()
    print(f"Chunks loaded: {len(chunks)}")
    print(f"Embedding model: {EMBEDDING_MODEL_NAME}")
    print(f"Collection name: {CHROMA_COLLECTION_NAME}")
    print(f"Database location: {CHROMA_PERSIST_DIR}")

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    # A full rebuild also clears stale ANN segment state for reused chunk IDs.
    # This directory is the dedicated Phase 3 vector store.
    if CHROMA_PERSIST_DIR.exists():
        shutil.rmtree(CHROMA_PERSIST_DIR)
    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    collection = client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "embedding_model": EMBEDDING_MODEL_NAME},
    )

    inserted = 0
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        # Scheme/title context is derived from each chunk's metadata, not from
        # question-specific rules. It reduces cross-scheme semantic collisions.
        embedding_texts = [
            f"Scheme: {item['scheme']}\nDocument: {item['title']}\n\n{item['text']}"
            for item in batch
        ]
        embeddings = model.encode(
            embedding_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        metadatas = [
            {field: str(item.get(field, "")) for field in METADATA_FIELDS}
            for item in batch
        ]
        collection.upsert(
            ids=[item["chunk_id"] for item in batch],
            documents=[item["text"] for item in batch],
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )
        inserted += len(batch)
        print(f"Indexed {inserted}/{len(chunks)} chunks")

    print(f"Chunks inserted or updated: {inserted}")
    print(f"Collection name: {collection.name}")
    print(f"Database location: {CHROMA_PERSIST_DIR}")
    print(f"Collection document count: {collection.count()}")


if __name__ == "__main__":
    main()
