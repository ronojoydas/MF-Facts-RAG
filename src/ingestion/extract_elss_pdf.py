"""Extract only HDFC ELSS - Tax Saver Fund pages from the August 2026 factsheet."""

from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "HDFC_ELSS_Tax_Saver_Factsheet_August_2026.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "chunks"
    / "HDFC_ELSS_Tax_Saver_Clean.txt"
)

# Pages 106-108 contain the minimum-application table (the ELSS row is on 107).
# Retain the existing scheme-specific and benchmark/riskometer pages as well.
ELSS_PAGES = {63, 64, 106, 107, 108, 115, 129}


def main():
    reader = PdfReader(PDF_PATH)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        for page_number in sorted(ELSS_PAGES):
            page = reader.pages[page_number - 1]
            text = page.extract_text() or ""

            output_file.write(f"\n{'=' * 80}\n")
            output_file.write(f"PAGE {page_number}\n")
            output_file.write(f"{'=' * 80}\n\n")
            output_file.write(text)
            output_file.write("\n")

    print("Source PDF pages:", len(reader.pages))
    print("ELSS pages extracted:", sorted(ELSS_PAGES))
    print("Clean ELSS text saved to:")
    print(OUTPUT_PATH)
    print("File size (bytes):", OUTPUT_PATH.stat().st_size)


if __name__ == "__main__":
    main()
