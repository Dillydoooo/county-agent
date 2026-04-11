import base64
import html
import re
from pathlib import Path

import streamlit as st
import fitz  # PyMuPDF

from src.utils.doc_helpers import (
    parsed_file_from_stem,
    read_text_file,
    raw_pdf_from_stem,
)

st.set_page_config(page_title="Document View", layout="wide")

st.markdown(
    """
    <style>
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

    .mobile-note {
        padding: 0.75rem 0.9rem;
        background: #f8fafc;
        border: 1px solid #dbe3ea;
        border-radius: 10px;
        margin-bottom: 1rem;
        font-size: 0.95rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def extract_tags(text: str):
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


def generate_summary(text: str):
    if not text:
        return {
            "summary": ["No summary available."],
            "date": "Unknown",
            "type": "Unknown",
            "tags": [],
        }

    lines = text.split("\n")
    clean_lines = [line.strip() for line in lines if line.strip()]

    date_match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
        text,
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
        "tags": extract_tags(text),
    }


def display_tag_pills(tags):
    if not tags:
        return ""

    pills = "".join(
        [f"<span class='tag-pill'>{html.escape(tag)}</span>" for tag in tags]
    )
    return f"<div class='doc-tags'>{pills}</div>"


def get_preview(text: str, max_chars: int = 5000):
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Preview truncated...]"


@st.cache_data
def render_pdf_pages(pdf_path_str: str, zoom: float = 1.2):
    pages = []
    pdf_path = Path(pdf_path_str)

    with fitz.open(pdf_path) as doc:
        for page in doc:
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pages.append(pix.tobytes("png"))

    return pages


doc_id = st.session_state.get("doc_id")

if not doc_id:
    st.error("No document selected.")
    if st.button("Back"):
        st.switch_page("app.py")
    st.stop()

parsed_path = parsed_file_from_stem(doc_id)

if not parsed_path:
    st.error("File not found.")
    if st.button("Back"):
        st.switch_page("app.py")
    st.stop()

text = read_text_file(parsed_path)
pdf_path = raw_pdf_from_stem(doc_id)
summary_data = generate_summary(text)

top1, top2 = st.columns([1, 5])

with top1:
    if st.button("← Back to list", use_container_width=True):
        st.switch_page("app.py")

with top2:
    st.subheader(parsed_path.name)

st.markdown("### Summary")
st.markdown(f"**Type:** {summary_data['type']}")
st.markdown(f"**Date:** {summary_data['date']}")

if summary_data["tags"]:
    st.markdown("**Tags:**")
    st.markdown(display_tag_pills(summary_data["tags"]), unsafe_allow_html=True)

st.markdown("---")

for line in summary_data["summary"]:
    st.write(line)

st.markdown("---")

text_bytes = text.encode("utf-8")
pdf_bytes = pdf_path.read_bytes() if pdf_path and pdf_path.exists() else None

col1, col2, col3 = st.columns(3)

with col1:
    text_b64 = base64.b64encode(text_bytes).decode("utf-8")
    st.markdown(
        f'<a href="data:text/plain;charset=utf-8;base64,{text_b64}" target="_blank">Open text in new tab</a>',
        unsafe_allow_html=True,
    )

with col2:
    st.download_button(
        label="Download text",
        data=text_bytes,
        file_name=parsed_path.name,
        mime="text/plain",
        key=f"download_text_{parsed_path.name}",
    )

with col3:
    if pdf_bytes:
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=pdf_path.name,
            mime="application/pdf",
            key=f"download_pdf_{parsed_path.name}",
        )

if pdf_path and pdf_path.exists():
    st.markdown("### View PDF Pages")
    st.markdown(
        "<div class='mobile-note'>On phone, scroll here to see the PDF pages rendered directly in the app.</div>",
        unsafe_allow_html=True,
    )

    try:
        page_images = render_pdf_pages(str(pdf_path), zoom=1.2)
        if not page_images:
            st.warning("PDF found, but no pages rendered.")
        else:
            for i, img in enumerate(page_images, start=1):
                st.image(img, caption=f"Page {i}", use_container_width=True)
    except Exception as e:
        st.warning(f"PDF render failed: {e}")
else:
    st.warning("No PDF found for this document.")

st.markdown("### Parsed Text")
st.text_area(
    "Document",
    get_preview(text, max_chars=5000),
    height=700,
    label_visibility="collapsed",
)