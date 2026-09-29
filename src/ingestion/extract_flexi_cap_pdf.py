"""Extract the HDFC Flexi Cap Fund pages from the existing combined factsheet."""

from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PDF_PATH = PROJECT_ROOT / "data" / "raw" / "HDFC_Flexi_Cap_Factsheet.pdf.pdf"
OUTPUT_PATH = PROJECT_ROOT / "data" / "chunks" / "HDFC_Flexi_Cap_Clean.txt"
SCHEME_TITLE = "HDFC Flexi Cap Fund"
FLEXI_CAP_PAGES = (7, 8)


def main():
    reader = PdfReader(PDF_PATH)
    if max(FLEXI_CAP_PAGES) > len(reader.pages):
        raise RuntimeError(f"Expected pages {FLEXI_CAP_PAGES} in {PDF_PATH.name}")
    matching_pages = [
        (page_number, reader.pages[page_number - 1].extract_text() or "")
        for page_number in FLEXI_CAP_PAGES
    ]
    if SCHEME_TITLE.casefold() not in matching_pages[0][1].casefold():
        raise RuntimeError(
            f"Page {FLEXI_CAP_PAGES[0]} does not contain {SCHEME_TITLE!r}; "
            "review page mapping before extraction."
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as output_file:
        for page_number, page_text in matching_pages:
            output_file.write(f"\n{'=' * 80}\nPAGE {page_number}\n{'=' * 80}\n\n")
            output_file.write(page_text)
            output_file.write("\n")

    print(f"Source PDF pages: {len(reader.pages)}")
    print("Flexi Cap pages extracted:", list(FLEXI_CAP_PAGES))
    print("Clean text saved to:", OUTPUT_PATH)
    print("File size (bytes):", OUTPUT_PATH.stat().st_size)


if __name__ == "__main__":
    main()
