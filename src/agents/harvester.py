import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

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
        href_lower = href.lower()

        if ".pdf" in href_lower:
            if href.startswith("http://") or href.startswith("https://"):
                full_url = href
            elif href.startswith("/"):
                full_url = urljoin(site_root, href)
            else:
                full_url = urljoin(site_root, "/" + href)

            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)

    print(f"Found {len(links)} PDF links.")
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

    saved_files = []

    for i, url in enumerate(pdf_links[:5], start=1):
        print(f"Downloading {i} of {min(len(pdf_links), 5)}: {url}")

        try:
            filename = safe_filename_from_url(url)
            filepath = os.path.join("data/raw", filename)

            response = requests.get(url, timeout=20)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(response.content)

            message = f"Saved: {filepath}"
            print(message)
            saved_files.append(message)

        except Exception as e:
            message = f"Failed: {url} -> {e}"
            print(message)
            saved_files.append(message)

    return "\n".join(saved_files)