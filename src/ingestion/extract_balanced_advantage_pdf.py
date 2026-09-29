"""Extract only HDFC Balanced Advantage Fund pages."""

from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "HDFC_Balanced_Advantage_Factsheet_August_2026.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "chunks"
    / "HDFC_Balanced_Advantage_Clean.txt"
)

BALANCED_ADVANTAGE_PAGES = {44, 45, 46, 47}


def main():
    reader = PdfReader(PDF_PATH)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        for page_number in sorted(BALANCED_ADVANTAGE_PAGES):
            page = reader.pages[page_number - 1]
            text = page.extract_text() or ""

            output_file.write(f"\n{'=' * 80}\n")
            output_file.write(f"PAGE {page_number}\n")
            output_file.write(f"{'=' * 80}\n\n")
            output_file.write(text)
            output_file.write("\n")

    print("Source PDF pages:", len(reader.pages))
    print(
        "Balanced Advantage pages extracted:",
        sorted(BALANCED_ADVANTAGE_PAGES),
    )
    print("Clean text saved to:")
    print(OUTPUT_PATH)
    print("File size (bytes):", OUTPUT_PATH.stat().st_size)


if __name__ == "__main__":
    main()