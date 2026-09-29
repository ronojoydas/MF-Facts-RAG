"""Print the curated source list. Does not download anything."""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "sources" / "sources.csv"


def main():
    with CSV_PATH.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        sources = list(reader)

    print("Total sources:", len(sources))
    print()

    for source in sources:
        print("source_id:", source["source_id"])
        print("source_type:", source["source_type"])
        print("title:", source["title"])
        print("url:", source["url"])
        print()


if __name__ == "__main__":
    main()
