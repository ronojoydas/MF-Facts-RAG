"""Check which selected HDFC schemes are present in the combined factsheet."""

from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "HDFC_MF_Factsheet_August_2026.pdf"
)

SCHEMES = [
    "HDFC Large Cap Fund",
    "HDFC Flexi Cap Fund",
    "HDFC ELSS Tax Saver Fund",
    "HDFC Small Cap Fund",
    "HDFC Balanced Advantage Fund",
]


def main():
    reader = PdfReader(PDF_PATH)

    all_text = ""

    for page in reader.pages:
        text = page.extract_text() or ""
        all_text += text + "\n"

    print("Total pages:", len(reader.pages))
    print()

    for scheme in SCHEMES:
        if scheme in all_text:
            print(scheme + ": FOUND")
        else:
            print(scheme + ": NOT FOUND")


if __name__ == "__main__":
    main()