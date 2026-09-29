"""Verify that all five curated schemes have valid metadata-rich chunks."""

import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
EXPECTED_SCHEMES = {
    "HDFC Large Cap Fund",
    "HDFC Flexi Cap Fund",
    "HDFC ELSS - Tax Saver Fund",
    "HDFC Small Cap Fund",
    "HDFC Balanced Advantage Fund",
}
REQUIRED_FIELDS = ("scheme", "source_id", "source_url", "publisher")


def main():
    if not CHUNKS_PATH.is_file():
        raise SystemExit(f"FAIL: chunks file does not exist: {CHUNKS_PATH}")

    counts = Counter()
    errors = []
    with CHUNKS_PATH.open(encoding="utf-8") as chunks_file:
        for line_number, line in enumerate(chunks_file, start=1):
            if not line.strip():
                errors.append(f"Line {line_number}: blank JSONL line")
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as error:
                errors.append(f"Line {line_number}: invalid JSON ({error})")
                continue

            counts[chunk.get("scheme", "")] += 1
            if not chunk.get("text", "").strip():
                errors.append(f"Line {line_number}: empty text")
            for field in REQUIRED_FIELDS:
                if not str(chunk.get(field, "")).strip():
                    label = "missing source URL" if field == "source_url" else f"missing {field}"
                    errors.append(f"Line {line_number}: {label}")

    missing_schemes = EXPECTED_SCHEMES - set(counts)
    if missing_schemes:
        errors.append("Missing schemes: " + ", ".join(sorted(missing_schemes)))

    for scheme in sorted(EXPECTED_SCHEMES):
        print(f"{scheme}: {counts.get(scheme, 0)} chunks")
    print(f"Total chunks: {sum(counts.values())}")

    if errors:
        print("Corpus verification failed:")
        for error in errors:
            print("-", error)
        raise SystemExit(1)
    print("Corpus verification passed.")


if __name__ == "__main__":
    main()
