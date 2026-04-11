import html
import re
from pathlib import Path
from datetime import datetime

import streamlit as st

from src.utils.doc_helpers import get_all_parsed_files

st.set_page_config(page_title="County Agent Alpha", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

st.markdown(
    """
    <style>
    .doc-title {
        font-size: 1.04rem;
        font-weight: 700;
        line-height: 1.45;
        margin-bottom: 0.35rem;
        color: #1f2937;
    }

    .doc-selected {
        display: inline-block;
        background: #e8f0ff;
        color: #174ea6;
        border: 1px solid #c6d6fb;
        border-radius: 999px;
        padding: 0.16rem 0.55rem;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }

    .doc-tags {
        margin-top: 0.15rem;
        margin-bottom: 0.1rem;
    }

    .tag-pill {
        display: inline-block;
        background: #eaf4ec;
        color: #24543a;
        border: 1px solid #bfd6c5;
        border-radius: 999px;
        padding: 0.18rem 0.52rem;
        margin: 0 0.28rem 0.28rem 0;
        font-size: 0.82rem;
        font-weight: 700;
        line-height: 1.2;
    }

    .tag-more {
        display: inline-block;
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #d8e0e8;
        border-radius: 999px;
        padding: 0.18rem 0.52rem;
        margin: 0 0.28rem 0.28rem 0;
        font-size: 0.82rem;
        font-weight: 700;
        line-height: 1.2;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def extract_tags(text):
    tags = set()
    lower = text.lower()

    if "executive session" in lower:
        tags.add("EXECUTIVE SESSION")
    if "litigation" in lower or "vs." in lower:
        tags.add("LITIGATION")
    if "budget" in lower:
        tags.add("BUDGET")
    if "tax" in lower or "levy" in lower:
        tags.add("TAX")
    if "hire" in lower or "hiring" in lower or "position" in lower:
        tags.add("HIRING")
    if "ordinance" in lower:
        tags.add("ORDINANCE")
    if "grant" in lower:
        tags.add("GRANT")
    if "zoning" in lower or "land use" in lower or "planning" in lower:
        tags.add("LAND USE")
    if "fire" in lower or "police" in lower or "sheriff" in lower:
        tags.add("PUBLIC SAFETY")
    if "legal" in lower or "counsel" in lower:
        tags.add("LEGAL")

    return sorted(tags)


@st.cache_data
def load_text_file(path_str):
    return Path(path_str).read_text(encoding="utf-8", errors="ignore")


def parse_date_from_filename(filename):
    match = re.match(r"^(\d{4}-\d{2}-\d{2})__", filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except Exception:
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


def list_parsed_files():
    files = get_all_parsed_files()

    def sort_key(path):
        dt = parse_date_from_filename(path.name)
        return (dt or datetime.min, path.name.lower())

    return sorted(files, key=sort_key, reverse=True)


def file_matches_search(path, query):
    if not query.strip():
        return True

    query = query.lower().strip()

    if query in clean_display_title(path).lower():
        return True

    try:
        return query in load_text_file(str(path)).lower()
    except Exception:
        return False


@st.cache_data
def get_file_tags(path_str):
    return extract_tags(load_text_file(path_str))


def file_matches_tags(path, selected_tags):
    if not selected_tags:
        return True

    file_tags = set(get_file_tags(str(path)))
    return bool(file_tags.intersection(selected_tags))


def display_tag_pills(tags, max_visible=None):
    if not tags:
        return ""

    visible_tags = tags if max_visible is None else tags[:max_visible]
    extra_count = 0 if max_visible is None else max(0, len(tags) - max_visible)

    pills = "".join([f"<span class='tag-pill'>{html.escape(tag)}</span>" for tag in visible_tags])

    if extra_count > 0:
        pills += f"<span class='tag-more'>+{extra_count} more</span>"

    return f"<div class='doc-tags'>{pills}</div>"


header_image_path = ASSETS_DIR / "rogue-river.jpg"

if header_image_path.exists():
    st.image(str(header_image_path), width=450)

st.title("County Research Agent v1")
st.caption("Searchable public records for Josephine County, Oregon")

st.markdown(
    """
**Josephine County Main Office**  
Phone: **(541) 474-5221**  
Website: **https://www.josephinecounty.gov**

This tool is for research and public access only.
"""
)

search_query = st.text_input("Search documents")

view_mode = st.radio(
    "View mode",
    options=["Side by side", "Stacked (better for mobile)"],
    horizontal=True,
)

all_files = list_parsed_files()
search_filtered_files = [f for f in all_files if file_matches_search(f, search_query)]

available_tags = sorted(
    {tag for f in search_filtered_files for tag in get_file_tags(str(f))}
)

selected_tags = st.multiselect(
    "Filter by tags",
    options=available_tags,
    default=[],
)

files = [f for f in search_filtered_files if file_matches_tags(f, selected_tags)]

st.subheader("Documents")
st.caption("Newest first")

list_container = st.container(height=780, border=True)

with list_container:
    if not files:
        st.write("No documents found.")
    else:
        for f in files:
            title = clean_display_title(f)
            row_tags = get_file_tags(str(f))

            row_box = st.container(border=True)

            with row_box:
                row_col1, row_col2 = st.columns([4.4, 1.6], gap="medium")

                with row_col1:
                    st.markdown(
                        f"<div class='doc-title'>{html.escape(title)}</div>",
                        unsafe_allow_html=True
                    )

                    if row_tags:
                        st.markdown(
                            display_tag_pills(row_tags, max_visible=3),
                            unsafe_allow_html=True
                        )

                with row_col2:
                    st.write("")
                    if st.button("View", key=f"open_{f.name}", use_container_width=True):
                        st.session_state["doc_id"] = f.stem
                        st.session_state["search_query"] = search_query
                        st.switch_page("pages/1_Document_View.py")