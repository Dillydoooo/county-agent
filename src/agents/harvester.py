import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

# FIX PATH FOR IMPORTS
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.parsers.pdf_parser import process_all_pdfs


# --- FILTER (TIGHT) ---
def is_relevant_pdf(url):
    url_lower = url.lower()

    include_keywords = [
        "agenda",
        "minutes",
        "packet",
        "weekly-business-session",
        "wbs",
        "executive-session",
        "admin-agenda",
        "legal-counsel",
        "hearing",
    ]

    exclude_keywords = [
        "application",
        "permit",
        "form",
        "rental",
        "brochure",
        "flyer",
        "job",
        "employment",
        "map",
        "guide",
        "starting-your-business",
        "rent-anne",
        "staff-report",
        "exhibits",
        "notice",
    ]

    if any(bad in url_lower for bad in exclude_keywords):
        return False

    return any(good in url_lower for good in include_keywords)


# --- SCRAPER ---
def get_pdf_links():
    page_url = "https://www.josephinecounty.gov/government/board_of_county_commissioners/agenda___minutes.php"
    site_root = "https://www.josephinecounty.gov/"

    print("Opening county agenda page...")
    response = requests.get(page_url, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        if ".pdf" in href.lower():
            if href.startswith("http"):
                full_url = href
            else:
                full_url = urljoin(site_root, href)

            if is_relevant_pdf(full_url) and full_url not in seen:
                seen.add(full_url)
                links.append(full_url)

    print(f"Filtered to {len(links)} relevant PDF links.")
    return links


# --- FILENAME CLEANUP ---
def safe_filename_from_url(url):
    path = urlparse(url).path
    name = os.path.basename(path)
    name = unquote(name)

    if not name.lower().endswith(".pdf"):
        name += ".pdf"

    # Normalize date → YYYY-MM-DD
    date_match = re.search(r'(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})', name)
    if date_match:
        m, d, y = date_match.groups()
        normalized_date = f"{y}-{int(m):02d}-{int(d):02d}"
        name = re.sub(r'\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4}', normalized_date, name)

    name = name.lower()
    name = name.replace(" ", "-")
    name = re.sub(r'[^a-z0-9\-.]', '', name)

    return name


# --- DOWNLOAD ---
def download_pdfs():
    pdf_links = get_pdf_links()

    if not pdf_links:
        return 0

    os.makedirs("data/raw", exist_ok=True)

    new_files = 0

    for i, url in enumerate(pdf_links[:15], start=1):
        print(f"Downloading {i} of {min(len(pdf_links), 15)}: {url}")

        try:
            filename = safe_filename_from_url(url)
            filepath = os.path.join("data/raw", filename)

            if os.path.exists(filepath):
                print(f"Skipping (already exists): {filename}")
                continue

            response = requests.get(url, timeout=20)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(response.content)

            print(f"Saved: {filepath}")
            new_files += 1

        except Exception as e:
            print(f"Failed: {url} -> {e}")

    return new_files


# --- MAIN PIPELINE ---
if __name__ == "__main__":
    print("\n--- START HARVEST ---\n")

    new_count = download_pdfs()
    print(f"\nNew PDFs downloaded: {new_count}")

    if new_count > 0:
        print("\n--- START PARSING (NEW FILES ONLY) ---\n")
        result = process_all_pdfs()
        print(result)
    else:
        print("\n--- SKIPPING PARSE (NO NEW FILES) ---\n")

    print("\n--- DONE ---\n")