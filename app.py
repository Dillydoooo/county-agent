import base64
import html
import re
from pathlib import Path
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="County Agent Alpha v3", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
PARSED_DIR = BASE_DIR / "data" / "parsed"
RAW_DIR = BASE_DIR / "data" / "raw"

def parse_date_from_filename(filename):
    match = re.match(r"^(\d{4}-\d{2}-\d{2})__", filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except:
            return None
    return None

def humanize_slug(slug):
    return slug.replace("-", " ").title()

def clean_display_title(parsed_file):
    stem = parsed_file.stem
    parts = stem.split("__")

    if len(parts) < 2:
        return parsed_file.name

    date_part = parts[0]
    slug_part = parts[1]

    suffix = ""
    if len(parts) > 2 and parts[2].isdigit():
        suffix = f" ({parts[2]})"

    return f"{date_part} | {humanize_slug(slug_part)}{suffix}"

def parsed_to_possible_pdf_names(parsed_file):
    stem = parsed_file.stem
    parts = stem.split("__")

    if len(parts) < 2:
        return []

    date_part = parts[0]
    slug_part = parts[1]

    try:
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        mmddyyyy = dt.strftime("%m-%d-%Y")
    except:
        return []

    candidates = []

    if slug_part == "document":
        candidates.append(f"{mmddyyyy}.pdf")
    else:
        candidates.append(f"{mmddyyyy} {humanize_slug(slug_part)}.pdf")

    return candidates

def find_matching_pdf(parsed_file):
    candidates = parsed_to_possible_pdf_names(parsed_file)
    for name in candidates:
        candidate = RAW_DIR / name
        if candidate.exists():
            return candidate
    return None

def load_text_file(path):
    return path.read_text(encoding="utf-8", errors="ignore")

def file_to_base64(path):
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def make_text_data_url(text):
    encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    return f"data:text/plain;base64,{encoded}"

def get_preview(text, max_chars=3000):
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Preview truncated...]"

def list_parsed_files():
    if not PARSED_DIR.exists():
        return []

    files = list(PARSED_DIR.glob("*.txt"))

    def sort_key(path):
        dt = parse_date_from_filename(path.name)
        return (dt or datetime.min, path.name)

    return sorted(files, key=sort_key, reverse=True)

def file_matches_search(path, query):
    if not query.strip():
        return True

    query = query.lower()

    if query in clean_display_title(path).lower():
        return True

    try:
        return query in load_text_file(path).lower()
    except:
        return False

def highlight_text(text, query):
    escaped = html.escape(text)

    if not query.strip():
        return f"<pre>{escaped}</pre>"

    pattern = re.compile(re.escape(query), re.IGNORECASE)

    def replacer(match):
        return f"<mark>{match.group(0)}</mark>"

    highlighted = pattern.sub(replacer, escaped)
    return f"<pre>{highlighted}</pre>"

if "selected_file" not in st.session_state:
    st.session_state.selected_file = None

st.title("County Research Agent v1")
st.caption("Alpha v3 public viewer")

search_query = st.text_input("Search documents")

files = list_parsed_files()
files = [f for f in files if file_matches_search(f, search_query)]

if st.session_state.selected_file:
    selected_path = Path(st.session_state.selected_file)

    if selected_path.exists():
        st.subheader(clean_display_title(selected_path))

        text = load_text_file(selected_path)
        pdf_path = find_matching_pdf(selected_path)

        st.markdown(f'<a href="{make_text_data_url(text)}" target="_blank">Open text in new tab</a>', unsafe_allow_html=True)

        st.download_button("Download text", text, file_name=selected_path.name)

        if pdf_path:
            st.download_button("Download PDF", pdf_path.read_bytes(), file_name=pdf_path.name)

        st.markdown(highlight_text(get_preview(text), search_query), unsafe_allow_html=True)

        if pdf_path:
            pdf_base64 = file_to_base64(pdf_path)
            st.markdown(f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="600"></iframe>', unsafe_allow_html=True)

st.divider()

for f in files:
    col1, col2 = st.columns([6,1])

    with col1:
        st.write(clean_display_title(f))

    with col2:
        if st.button("Open", key=f.name):
            st.session_state.selected_file = str(f)
            st.rerun()