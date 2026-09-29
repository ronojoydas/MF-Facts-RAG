"""Verify persisted ChromaDB documents and their metadata."""

import chromadb

from src.config import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR


REQUIRED_METADATA = (
    "scheme",
    "source_id",
    "source_type",
    "title",
    "source_url",
    "publisher",
    "last_updated",
)


def main():
    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    try:
        collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    except Exception as error:
        raise SystemExit(f"Could not open collection {CHROMA_COLLECTION_NAME!r}: {error}")

    result = collection.get(include=["documents", "metadatas"])
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    errors = []
    schemes = set()

    if not documents:
        errors.append("Collection contains no documents")
    if len(documents) != len(metadatas):
        errors.append("Document and metadata counts do not match")

    for index, (document, metadata) in enumerate(zip(documents, metadatas), start=1):
        if not document or not document.strip():
            errors.append(f"Document {index} is empty")
        if not metadata:
            errors.append(f"Document {index} has no metadata")
            continue
        schemes.add(metadata.get("scheme", ""))
        missing = [field for field in REQUIRED_METADATA if field not in metadata]
        if missing:
            errors.append(f"Document {index} is missing metadata: {missing}")

    print(f"Collection name: {collection.name}")
    print(f"Stored documents: {collection.count()}")
    print("Schemes represented:")
    for scheme in sorted(filter(None, schemes)):
        print(f"- {scheme}")
    print(f"Metadata and documents present: {'yes' if not errors else 'no'}")

    if errors:
        print("Verification failed:")
        for error in errors:
            print("-", error)
        raise SystemExit(1)
    print("Vector store verification passed.")


if __name__ == "__main__":
    main()
