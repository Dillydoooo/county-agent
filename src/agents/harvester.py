import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

# IMPORT YOUR PARSER
from src.parsers.pdf_parser import process_all_pdfs


def is_relevant_pdf(url):
    url_lower = url.lower()

    keywords = [
        "agenda",
        "minutes",
        "packet",
        "hearing",
        "session",
        "board",
    ]

    return any(k in url_lower for k in keywords)


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


def safe_filename_from_url(url):
    path = urlparse(url).path
    name = os.path.basename(path)
    name = unquote(name)

    if not name.lower().endswith(".pdf"):
        name += ".pdf"

    bad_chars = '<>:"/\\|?*'
    for ch in bad_chars:
        name = name.replace(ch, "_")

    return name


def download_pdfs():
    pdf_links = get_pdf_links()

    if not pdf_links:
        return "No PDF links found."

    os.makedirs("data/raw", exist_ok=True)

    new_files = 0

    for i, url in enumerate(pdf_links[:10], start=1):
        print(f"Downloading {i} of {min(len(pdf_links), 10)}: {url}")

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


if __name__ == "__main__":
    print("\n--- START HARVEST ---\n")

    new_count = download_pdfs()

    print(f"\nNew PDFs downloaded: {new_count}")

    print("\n--- START PARSING ---\n")

    result = process_all_pdfs()

    print(result)

    print("\n--- DONE ---\n")