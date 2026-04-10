import os
import re
import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path):
    text_parts = []

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            text_parts.append(f"\n--- Page {page_num} ---\n")
            text_parts.append(page_text)

    return "".join(text_parts)

def clean_filename(name):
    name = os.path.splitext(name)[0]

    # normalize spaces and separators
    name = name.strip().lower()
    name = name.replace("&", "and")
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")

    return name

def extract_date_prefix(name):
    patterns = [
        r"(\d{2})-(\d{2})-(\d{4})",   # 04-08-2026
        r"(\d{1})-(\d{1,2})-(\d{4})", # 4-8-2026
        r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", # 3.11.26 or 03.12.2026
    ]

    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            parts = match.groups()

            if "." in match.group(0):
                month = int(parts[0])
                day = int(parts[1])
                year = int(parts[2])
                if year < 100:
                    year += 2000
            else:
                month = int(parts[0])
                day = int(parts[1])
                year = int(parts[2])

            return f"{year:04d}-{month:02d}-{day:02d}"

    return "unknown-date"

def build_output_filename(pdf_filename, used_names):
    date_part = extract_date_prefix(pdf_filename)
    clean_part = clean_filename(pdf_filename)

    # remove repeated date text from clean part if present
    clean_part = re.sub(r"^\d{1,2}[-.]\d{1,2}[-.]\d{2,4}-?", "", clean_part)
    clean_part = re.sub(r"^\d{1,2}-\d{1,2}-\d{4}-?", "", clean_part)
    clean_part = clean_part.strip("-")

    if not clean_part:
        clean_part = "document"

    base_name = f"{date_part}__{clean_part}.txt"
    final_name = base_name
    counter = 2

    while final_name in used_names:
        final_name = f"{date_part}__{clean_part}__{counter}.txt"
        counter += 1

    used_names.add(final_name)
    return final_name

def process_all_pdfs():
    raw_folder = "data/raw"
    parsed_folder = "data/parsed"

    os.makedirs(parsed_folder, exist_ok=True)

    results = []
    used_names = set()

    for existing in os.listdir(parsed_folder):
        used_names.add(existing)

    for filename in os.listdir(raw_folder):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(raw_folder, filename)

            try:
                text = extract_text_from_pdf(pdf_path)
                txt_filename = build_output_filename(filename, used_names)
                txt_path = os.path.join(parsed_folder, txt_filename)

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)

                message = f"Parsed: {txt_path}"
                print(message)
                results.append(message)

            except Exception as e:
                message = f"Failed: {pdf_path} -> {e}"
                print(message)
                results.append(message)

    if not results:
        return "No PDFs found in data/raw."

    return "\n".join(results)