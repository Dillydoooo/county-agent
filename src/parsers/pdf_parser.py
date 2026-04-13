import os
from pathlib import Path
import fitz
import re

RAW_DIR = Path("data/raw")
PARSED_DIR = Path("data/parsed")

PARSED_DIR.mkdir(parents=True, exist_ok=True)


def normalize_name(name):
    name = name.lower()

    name = re.sub(r'(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})',
                  lambda m: f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}",
                  name)

    name = name.replace(" ", "-")
    name = re.sub(r'[^a-z0-9\-]', '', name)

    return name


def extract_date(name):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', name)
    if match:
        return match.group(1)
    return "no-date"


def parse_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = ""

        for page in doc:
            text += page.get_text()

        return text.strip()
    except Exception as e:
        print(f"Failed parsing {file_path}: {e}")
        return None


def process_all_pdfs():
    results = []
    seen = set()  # <-- THIS FIXES DUPLICATES

    for pdf_file in RAW_DIR.glob("*.pdf"):
        clean_name = normalize_name(pdf_file.stem)

        if clean_name in seen:
            continue
        seen.add(clean_name)

        date_part = extract_date(clean_name)

        text = parse_pdf(pdf_file)

        if not text:
            continue

        filename = f"{date_part}__{clean_name}.txt"
        save_path = PARSED_DIR / filename

        if save_path.exists():
            continue

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)

        message = f"Parsed: {save_path}"
        print(message)
        results.append(message)

    if not results:
        print("No new PDFs to parse.")
    else:
        print("\n".join(results))


if __name__ == "__main__":
    print("\n--- MANUAL PARSE RUN ---\n")
    process_all_pdfs()
    print("\n--- DONE ---\n")