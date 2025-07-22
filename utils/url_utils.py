import io
from urllib.parse import urlparse, parse_qs, urlencode

import httpx
import pypdf
from bs4 import BeautifulSoup


def get_domain(url: str) -> str:
    """Extracts the domain from a URL."""
    # Use httpx's URL parsing for robustness
    try:
        parsed_url = httpx.URL(url)
        host = parsed_url.host
        if host and host.startswith("www."):
            return host[4:]  # Remove 'www.' for consistent comparison
        return host
    except httpx.InvalidURL:
        return ""

def normalize_url(url: str) -> str:
    """Normalizes a URL for consistent comparison (removes fragments, sorts query params)."""
    try:
        # Parse the URL using urllib.parse for robust query string handling
        parsed_url_urllib = urlparse(url)

        # Parse the query string into a dictionary of lists (e.g., {'param': ['value1', 'value2']})
        query_params_dict = parse_qs(parsed_url_urllib.query)

        # Flatten the dictionary into a list of (key, value) tuples and sort them
        # This handles cases where a parameter might have multiple values
        sorted_query_items = []
        for key in sorted(query_params_dict.keys()):
            for value in sorted(query_params_dict[key]):
                sorted_query_items.append((key, value))

        # Re-encode the sorted query parameters back into a query string
        sorted_query_string = urlencode(sorted_query_items)

        # Reconstruct the URL, replacing the query and removing the fragment
        normalized_url = parsed_url_urllib._replace(
            query=sorted_query_string,
            fragment=""
        ).geturl()

        return normalized_url
    except Exception:
        return url # Return original if invalid

def get_all_urls(data: BeautifulSoup, domain: str):
    urls = []
    seen = set()
    if data:
        url_elements = data.select("a[href]")
        for url_element in url_elements:
            href = url_element['href'].split('?')[0]  # remove URL params
            if href.endswith("/"):
                href = href[:-1]

            if href.startswith("/"):
                href = "https://" + domain + href

            href_lower = href.lower()

            # Skip media files
            media_extensions = (
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
                '.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv',
                '.mp3', '.wav', '.ogg', '.webm',
                '.ico', '.zip', '.rar', '.tar', '.gz', '.doc', '.docx', '.ppt', '.xls'
            )
            if any(href_lower.endswith(ext) for ext in media_extensions):
                continue

            if href.startswith("http://") or href.startswith("https://"):
                if href not in seen:
                    seen.add(href)
                    urls.append(href)
            elif href.endswith(".php") or href.endswith(".pdf"):
                new_href = None
                if domain.startswith("http"):
                    new_href = domain + "/" + href
                else:
                    new_href = "https://" + domain + "/" + href

                if new_href is None:
                    continue

                if new_href not in seen:
                    seen.add(new_href)
                    urls.append(new_href)

    return urls

async def extract_text_from_pdf_url(url: str) -> str:
    """
    Downloads a PDF from a URL and extracts all text from it.
    """
    print(f"Attempting to extract text from PDF: {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=60.0)
            response.raise_for_status()
            pdf_bytes = response.content

        # Use pypdf to read the PDF from bytes
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or "" # extract_text() can return None

        if not text.strip():
            print(f"No text extracted from PDF: {url}")
        return text
    except httpx.HTTPStatusError as e:
        print(f"HTTP error downloading PDF {url}: {e.response.status_code} - {e.response.text}")
        return ""
    except Exception as e:
        print(f"Error extracting text from PDF {url}: {e}")
        return ""
