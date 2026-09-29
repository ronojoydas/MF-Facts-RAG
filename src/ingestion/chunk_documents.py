"""Create overlapping, metadata-rich JSONL chunks from curated clean text."""

import csv
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES_PATH = PROJECT_ROOT / "data" / "sources" / "sources.csv"
CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"

DOCUMENTS = [
    ("HDFC Large Cap Fund", "HDFC001", "HDFC_Large_Cap_Factsheet_August_2026.txt"),
    ("HDFC Flexi Cap Fund", "HDFC002", "HDFC_Flexi_Cap_Clean.txt"),
    ("HDFC ELSS - Tax Saver Fund", "HDFC003", "HDFC_ELSS_Tax_Saver_Clean.txt"),
    ("HDFC Small Cap Fund", "HDFC004", "HDFC_Small_Cap_Factsheet_August_2026.txt"),
    ("HDFC Balanced Advantage Fund", "HDFC005", "HDFC_Balanced_Advantage_Clean.txt"),
]


MAX_CHUNK_CHARS = 900
TABLE_HEADER_RE = re.compile(
    r"^SCHEME\s+NAME\b.*\bMINIMUM\s+APPLICATION\s+AMOUNT\b", re.IGNORECASE
)
TABLE_PURCHASE_ROW_RE = re.compile(
    r"^HDFC\b.*\b(?:Fund|FOF)\b.*\bPurchase(?:\s*/\s*Additional\s+Purchase)?\b",
    re.IGNORECASE,
)
OBJECTIVE_LABEL_RE = re.compile(r"^INVESTMENT\s+OBJECTIVE\s*$", re.IGNORECASE)
ATOMIC_FACT_HEADING_RE = re.compile(
    r"^#*\s*(?:INVESTMENT\s+OBJECTIVE|BENCHMARK(?:\s+INDEX)?|"
    r"MINIMUM\s+APPLICATION\s+AMOUNT|EXPENSE\s+RATIO|"
    r"LOCK[- ]IN\s+PERIOD|EXIT\s+LOAD|ASSETS\s+UNDER\s+MANAGEMENT|AUM)\b",
    re.IGNORECASE,
)


def is_heading(line):
    """Recognize structural labels, not ordinary prose mentioning a scheme name."""
    value = line.strip()
    if not value or len(value) > 130:
        return False
    if value.startswith("#"):
        return True
    if OBJECTIVE_LABEL_RE.fullmatch(value):
        return True
    if re.fullmatch(
        r"(?:category(?: of scheme)?|fund facts|benchmark(?: index)?|"
        r"minimum application amount|plans?\s*&\s*options|exit load|"
        r"lock[- ]in period|expense ratio|net equity exposure)",
        value,
        re.IGNORECASE,
    ):
        return True

    letters = [char for char in value if char.isalpha()]
    return bool(letters) and value == value.upper() and not value.endswith(".")


def semantic_blocks(page_text):
    """Keep short headings with the content that follows them on the same page."""
    blocks = []
    current = []
    pending_headings = []

    def flush_current():
        nonlocal current, pending_headings
        if current:
            blocks.append("\n".join(current).strip())
            current = []

    for raw_line in page_text.splitlines():
        line = raw_line.strip()
        if not line:
            flush_current()
            continue

        # The source often puts a complete objective after its label on the
        # same line. Keep that statement as one fact block, separate from the
        # adjacent fund-manager, NAV, and portfolio sections.
        if re.match(r"^INVESTMENT\s+OBJECTIVE\s*:", line, re.IGNORECASE):
            flush_current()
            if pending_headings:
                current.extend(pending_headings)
                pending_headings = []
            current.append(line)
            continue

        if is_heading(line):
            flush_current()
            pending_headings.append(line)
            continue

        if pending_headings:
            current.extend(pending_headings)
            pending_headings = []
        current.append(line)

    flush_current()
    if pending_headings:
        blocks.append("\n".join(pending_headings))
    return blocks


def split_oversized_block(block, limit=MAX_CHUNK_CHARS):
    """Split long table/list blocks at line or word boundaries, never mid-word."""
    if len(block) <= limit:
        return [block]

    parts = []
    lines = block.splitlines()
    current = []
    current_size = 0
    for line in lines:
        if len(line) > limit:
            if current:
                parts.append("\n".join(current).strip())
                current, current_size = [], 0
            words = line.split()
            word_group = []
            word_size = 0
            for word in words:
                extra = len(word) + (1 if word_group else 0)
                if word_group and word_size + extra > limit:
                    parts.append(" ".join(word_group))
                    word_group, word_size = [], 0
                word_group.append(word)
                word_size += len(word) + (1 if len(word_group) > 1 else 0)
            if word_group:
                parts.append(" ".join(word_group))
            continue

        extra = len(line) + (1 if current else 0)
        if current and current_size + extra > limit:
            parts.append("\n".join(current).strip())
            current, current_size = [], 0
        current.append(line)
        current_size += len(line) + (1 if len(current) > 1 else 0)

    if current:
        parts.append("\n".join(current).strip())
    return [part for part in parts if part]


def pack_blocks(blocks, limit=MAX_CHUNK_CHARS):
    """Pack ordinary blocks while keeping atomic facts in their own chunks."""
    chunks = []
    current = ""
    for block in blocks:
        if ATOMIC_FACT_HEADING_RE.match(block.splitlines()[0].strip()):
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(split_oversized_block(block, limit))
            continue
        for part in split_oversized_block(block, limit):
            candidate = f"{current}\n\n{part}" if current else part
            if current and len(candidate) > limit:
                chunks.append(current)
                current = part
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks


def chunk_page(page, scheme, table_context=""):
    """Chunk one page; isolate recognizable purchase rows with their table label."""
    lines = page.splitlines()
    if not table_context:
        page_chunks = pack_blocks(semantic_blocks(page))
        return [
            chunk if scheme.casefold() in chunk.casefold() else f"Scheme: {scheme}\n\n{chunk}"
            for chunk in page_chunks
        ]

    chunks = []
    ordinary_lines = []

    def flush_ordinary():
        nonlocal ordinary_lines
        if ordinary_lines:
            ordinary_text = "\n".join(ordinary_lines).strip()
            ordinary_lines = []
            chunks.extend(pack_blocks(semantic_blocks(ordinary_text)))

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not TABLE_PURCHASE_ROW_RE.match(line):
            ordinary_lines.append(lines[index])
            index += 1
            continue

        flush_ordinary()
        row_lines = [line]
        index += 1
        while index < len(lines):
            following = lines[index].strip()
            if TABLE_PURCHASE_ROW_RE.match(following):
                break
            row_lines.append(lines[index])
            index += 1
        row_text = f"{table_context}\n\n" + "\n".join(row_lines).strip()
        chunks.extend(split_oversized_block(row_text))

    flush_ordinary()
    return [
        chunk if scheme.casefold() in chunk.casefold() else f"Scheme: {scheme}\n\n{chunk}"
        for chunk in chunks
    ]


def load_sources():
    with SOURCES_PATH.open(newline="", encoding="utf-8-sig") as source_file:
        return {row["source_id"]: row for row in csv.DictReader(source_file)}


def publisher_for(source_type):
    return {"AMC": "HDFC Mutual Fund", "SEBI": "SEBI", "AMFI": "AMFI"}.get(
        source_type, source_type
    )


def main():
    sources = load_sources()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    counts = {}
    chunk_number = 0

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as output_file:
        for scheme, source_id, filename in DOCUMENTS:
            if source_id not in sources:
                raise ValueError(f"Source ID {source_id} is missing from {SOURCES_PATH}")
            source = sources[source_id]
            source_url = source.get("url", "").strip()
            if not source_url:
                raise ValueError(f"Source ID {source_id} has no URL")

            text_path = CHUNKS_DIR / filename
            if not text_path.is_file():
                raise FileNotFoundError(f"Clean text document not found: {text_path}")
            clean_text = text_path.read_text(encoding="utf-8").strip()
            if not clean_text:
                raise ValueError(f"Clean text document is empty: {text_path}")

            # Keep pages separate and carry only a structurally recognized
            # table header onto its continuation pages.
            pages = re.split(r"(?=\n={20,}\nPAGE \d+\n={20,}\n)", clean_text)
            chunks = []
            carried_table_header = ""
            continuation_pages = 0
            for page in pages:
                page = page.strip()
                lines = [line.strip() for line in page.splitlines() if line.strip()]
                table_header = next(
                    (line for line in lines if TABLE_HEADER_RE.match(line)), None
                )
                if table_header:
                    carried_table_header = table_header
                    continuation_pages = 2
                    context = table_header
                else:
                    context = carried_table_header if continuation_pages else ""
                    if continuation_pages:
                        continuation_pages -= 1
                    else:
                        carried_table_header = ""

                page_chunks = chunk_page(page, scheme, context)
                for page_chunk in page_chunks:
                    if context and context.casefold() not in page_chunk.casefold():
                        page_chunk = f"{context}\n\n{page_chunk}"
                    chunks.append(page_chunk)
            counts[scheme] = len(chunks)
            for index, chunk in enumerate(chunks, start=1):
                record = {
                    "chunk_id": f"{source_id}_{index:04d}",
                    "scheme": scheme,
                    "source_id": source_id,
                    "source_type": source.get("source_type", "").strip(),
                    "title": source.get("title", "").strip(),
                    "source_url": source_url,
                    "publisher": publisher_for(source.get("source_type", "").strip()),
                    "last_updated": source.get("last_updated", "").strip(),
                    "text": chunk,
                }
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                chunk_number += 1

    for scheme, count in counts.items():
        print(f"{scheme}: {count} chunks")
    print(f"Total chunks: {chunk_number}")
    print(f"Saved chunks to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
