from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PARSED_DIR = BASE_DIR / "data" / "parsed"
RAW_DIR = BASE_DIR / "data" / "raw"


def get_all_parsed_files():
    if not PARSED_DIR.exists():
        return []
    return sorted(PARSED_DIR.glob("*.txt"), reverse=True)


def display_label_from_path(path: Path):
    return path.stem.replace("_", " ")


def parsed_file_from_stem(doc_id: str):
    p = PARSED_DIR / f"{doc_id}.txt"
    return p if p.exists() else None


def read_text_file(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def humanize_slug(slug: str):
    return slug.replace("-", " ").title()


def parsed_to_possible_pdf_names_from_stem(doc_id: str):
    parts = doc_id.split("__")

    if len(parts) < 2:
        return []

    date_part = parts[0]
    slug_part = parts[1]

    try:
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        mmddyyyy = dt.strftime("%m-%d-%Y")
    except Exception:
        return []

    candidates = []

    if slug_part == "document":
        candidates.append(f"{mmddyyyy}.pdf")
    else:
        candidates.append(f"{mmddyyyy} {humanize_slug(slug_part)}.pdf")

    return candidates


def raw_pdf_from_stem(doc_id: str):
    candidates = parsed_to_possible_pdf_names_from_stem(doc_id)

    for name in candidates:
        p = RAW_DIR / name
        if p.exists():
            return p

    return None