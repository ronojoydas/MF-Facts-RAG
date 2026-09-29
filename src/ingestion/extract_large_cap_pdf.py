"""Extract text from the HDFC Large Cap Fund August 2026 factsheet."""

from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "HDFC_Large_Cap_Factsheet_August_2026.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "chunks"
    / "HDFC_Large_Cap_Factsheet_August_2026.txt"
)


def main():
    reader = PdfReader(PDF_PATH)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            output_file.write(f"\n{'=' * 80}\n")
            output_file.write(f"PAGE {page_number}\n")
            output_file.write(f"{'=' * 80}\n\n")
            output_file.write(text)
            output_file.write("\n")

    print("PDF pages:", len(reader.pages))
    print("Extracted text saved to:")
    print(OUTPUT_PATH)
    print("File size (bytes):", OUTPUT_PATH.stat().st_size)


if __name__ == "__main__":
    main()