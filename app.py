import base64
import html
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

import streamlit as st

st.set_page_config(page_title="County Agent Alpha v6.5", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
PARSED_DIR = BASE_DIR / "data" / "parsed"
RAW_DIR = BASE_DIR / "data" / "raw"
ASSETS_DIR = BASE_DIR / "assets"

GITHUB_OWNER = "Dillydoooo"
GITHUB_REPO = "county-agent"
GITHUB_BRANCH = "main"


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------
if "selected_file" not in st.session_state:
    st.session_state.selected_file = None

if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Stacked (better for mobile)"


# ---------------------------------------------------------
# STYLES
# ---------------------------------------------------------
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

    .helper-text {
        font-size: 0.92rem;
        color: #475569;
    }

    div.stButton > button {
        min-height: 2.6rem;
        font-weight: 600;
    }

    @media (max-width: 900px) {
        .doc-title {
            font-size: 1.1rem;
        }

        .tag-pill, .tag-more {
            font-size: 0.88rem;
            padding: 0.22rem 0.58rem;
        }

        .helper-text {
            font-size: 0.96rem;
        }

        div.stButton > button {
            min-height: 3rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# TAGGING / SUMMARY
# ---------------------------------------------------------
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


def generate_summary(text):
    if not text:
        return {
            "summary": ["No summary available."],
            "date": "Unknown",
            "type": "Unknown",
            "tags": []
        }

    lines = text.split("\n")
    clean_lines = [line.strip() for line in lines if line.strip()]

    date_match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
        text
    )
    date_str = date_match.group(0) if date_match else "Date not detected"

    lower_text = text.lower()
    doc_type = "General Document"
    if "legal counsel update" in lower_text:
        doc_type = "Legal Counsel Update"
    elif "agenda" in lower_text:
        doc_type = "Agenda"
    elif "minutes" in lower_text:
        doc_type = "Meeting Minutes"
    elif "packet" in lower_text:
        doc_type = "Meeting Packet"

    skip_phrases = [
        "accommodations",
        "hearing-impaired",
        "tdd",
        "notify",
        "48-hours",
        "livestream",
        "youtube",
        "board of commissioners",
        "ron smith",
        "colene martin",
        "gary richardson",
    ]

    agenda = []
    sub_items = []

    for line in clean_lines:
        lower = line.lower()

        if any(p in lower for p in skip_phrases):
            continue

        if re.match(r"^\d+\.", line):
            agenda.append(line)
        elif re.match(r"^[a-zA-Z]\.", line):
            sub_items.append(line)

    summary_output = []

    for item in agenda:
        label = re.sub(r"^\d+\.\s*", "", item)

        if "executive session" in label.lower():
            summary_output.append(f"• {label}")

            for sub in sub_items:
                clean_sub = re.sub(r"^[a-zA-Z]\.\s*", "", sub)
                clean_sub = clean_sub.split(" – ORS")[0].strip()
                summary_output.append(f"  - {clean_sub}")

            continue

        if any(k in label.lower() for k in ["approval", "other", "announcements"]):
            summary_output.append(f"• {label}")

    if not summary_output:
        fallback = []
        for line in clean_lines:
            if len(line) > 40 and not line.lower().startswith("http"):
                fallback.append(f"• {line}")
            if len(fallback) >= 3:
                break
        summary_output = fallback or ["• Summary could not be generated."]

    return {
        "summary": summary_output,
        "date": date_str,
        "type": doc_type,
        "tags": extract_tags(text)
    }


# ---------------------------------------------------------
# FILE HELPERS
# ---------------------------------------------------------
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
    except Exception:
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


@st.cache_data
def load_text_file(path_str):
    path = Path(path_str)
    return path.read_text(encoding="utf-8", errors="ignore")


def get_preview(text, max_chars=5000):
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Preview truncated...]"


def list_parsed_files():
    if not PARSED_DIR.exists():
        return []

    files = list(PARSED_DIR.glob("*.txt"))

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
    text = load_text_file(path_str)
    return extract_tags(text)


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

    pills = "".join(
        [f"<span class='tag-pill'>{html.escape(tag)}</span>" for tag in visible_tags]
    )

    if extra_count > 0:
        pills += f"<span class='tag-more'>+{extra_count} more</span>"

    return f"<div class='doc-tags'>{pills}</div>"


def highlight_text(text, query):
    escaped = html.escape(text)

    if not query.strip():
        return (
            "<pre style='white-space: pre-wrap; word-wrap: break-word; "
            "font-family: sans-serif; font-size: 15px; line-height: 1.6;'>"
            f"{escaped}</pre>"
        )

    pattern = re.compile(re.escape(query), re.IGNORECASE)

    def replacer(match):
        return f"<mark>{match.group(0)}</mark>"

    highlighted = pattern.sub(replacer, escaped)
    return (
        "<pre style='white-space: pre-wrap; word-wrap: break-word; "
        "font-family: sans-serif; font-size: 15px; line-height: 1.6;'>"
        f"{highlighted}</pre>"
    )


def github_blob_url_for_pdf(pdf_path):
    relative_path = pdf_path.relative_to(BASE_DIR).as_posix()
    encoded_path = quote(relative_path, safe="/")
    return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/blob/{GITHUB_BRANCH}/{encoded_path}"


def select_document(path_obj):
    st.session_state.selected_file = str(path_obj)


# ---------------------------------------------------------
# RENDERERS
# ---------------------------------------------------------
def render_document_list(files, stacked_mode=False):
    st.subheader("Documents")
    st.caption("Newest first")

    list_container = st.container(border=True)

    with list_container:
        if not files:
            st.write("No documents found.")
            return

        for f in files:
            is_selected = str(f) == st.session_state.selected_file
            title = clean_display_title(f)
            row_tags = get_file_tags(str(f))

            row_box = st.container(border=True)

            with row_box:
                if stacked_mode:
                    if is_selected:
                        st.markdown(
                            "<div class='doc-selected'>Selected</div>",
                            unsafe_allow_html=True
                        )

                    st.markdown(
                        f"<div class='doc-title'>{html.escape(title)}</div>",
                        unsafe_allow_html=True
                    )

                    if row_tags:
                        st.markdown(
                            display_tag_pills(row_tags, max_visible=3),
                            unsafe_allow_html=True
                        )

                    if st.button(
                        "View document",
                        key=f"open_mobile_{f.name}",
                        use_container_width=True
                    ):
                        select_document(f)
                        st.rerun()

                else:
                    row_col1, row_col2 = st.columns([4.0, 2.0], gap="medium")

                    with row_col1:
                        if is_selected:
                            st.markdown(
                                "<div class='doc-selected'>Selected</div>",
                                unsafe_allow_html=True
                            )

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
                        if st.button(
                            "View",
                            key=f"open_desktop_{f.name}",
                            use_container_width=True
                        ):
                            select_document(f)
                            st.rerun()


def render_selected_document(search_query):
    if not st.session_state.selected_file:
        st.info("Select a document from the list.")
        return

    selected_path = Path(st.session_state.selected_file)

    if not selected_path.exists():
        st.warning("Selected document no longer exists.")
        return

    st.subheader(clean_display_title(selected_path))

    text = load_text_file(str(selected_path))
    pdf_path = find_matching_pdf(selected_path)
    summary_data = generate_summary(text)

    st.markdown("### Summary")
    st.markdown(f"**Type:** {summary_data['type']}")
    st.markdown(f"**Date:** {summary_data['date']}")

    if summary_data["tags"]:
        st.markdown("**Tags:**", help="Topics detected in this document.")
        st.markdown(
            display_tag_pills(summary_data["tags"]),
            unsafe_allow_html=True
        )

    st.markdown("---")

    for line in summary_data["summary"]:
        st.write(line)

    st.markdown("---")

    text_bytes = text.encode("utf-8")
    pdf_bytes = pdf_path.read_bytes() if pdf_path else None

    action_col1, action_col2 = st.columns(2)
    action_col3, action_col4 = st.columns(2)

    with action_col1:
        text_b64 = base64.b64encode(text_bytes).decode("utf-8")
        st.markdown(
            f'<a href="data:text/plain;charset=utf-8;base64,{text_b64}" target="_blank">Open text in new tab</a>',
            unsafe_allow_html=True
        )

    with action_col2:
        st.download_button(
            label="Download text",
            data=text_bytes,
            file_name=selected_path.name,
            mime="text/plain",
            key=f"download_text_{selected_path.name}"
        )

    with action_col3:
        if pdf_path and pdf_bytes:
            st.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name=pdf_path.name,
                mime="application/pdf",
                key=f"download_pdf_{selected_path.name}"
            )

    with action_col4:
        if pdf_path:
            pdf_url = github_blob_url_for_pdf(pdf_path)
            st.link_button("View Original PDF", pdf_url)

    st.markdown(
        highlight_text(get_preview(text, max_chars=5000), search_query),
        unsafe_allow_html=True
    )

    if not pdf_path:
        st.warning("PDF not found for this document.")


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
header_image_path = ASSETS_DIR / "rogue-river.jpg"

if header_image_path.exists():
    st.image(str(header_image_path), width=450)
else:
    st.info("Header image not found. Add assets/rogue-river.jpg")

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


# ---------------------------------------------------------
# FILTERS
# ---------------------------------------------------------
search_query = st.text_input("Search documents")

view_mode = st.radio(
    "View mode",
    options=["Side by side", "Stacked (better for mobile)"],
    horizontal=True,
    key="view_mode",
    help="Use stacked mode on phones or when you want larger reading areas."
)

all_files = list_parsed_files()
search_filtered_files = [f for f in all_files if file_matches_search(f, search_query)]

available_tags = sorted(
    {
        tag
        for f in search_filtered_files
        for tag in get_file_tags(str(f))
    }
)

selected_tags = st.multiselect(
    "Filter by tags",
    options=available_tags,
    default=[],
    help="Show documents that match any selected tag."
)

files = [f for f in search_filtered_files if file_matches_tags(f, selected_tags)]


# ---------------------------------------------------------
# MAIN LAYOUT
# ---------------------------------------------------------
if view_mode == "Side by side":
    left_col, right_col = st.columns([1.45, 2.1], gap="large")

    with left_col:
        render_document_list(files, stacked_mode=False)

    with right_col:
        render_selected_document(search_query)

else:
    render_selected_document(search_query)
    st.markdown("---")
    render_document_list(files, stacked_mode=True)