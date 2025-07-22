import os
import re

# Base directory for all scraped data and FAISS indexes
BASE_SCRAPED_DATA_DIR = "scraped_pages"

def get_scrape_dir(scrape_id: str) -> str:
    """Returns the base directory for a specific scrape ID."""
    return os.path.join(BASE_SCRAPED_DATA_DIR, scrape_id)

def get_pages_dir(scrape_id: str) -> str:
    """Returns the directory where individual scraped page contents are stored."""
    return os.path.join(get_scrape_dir(scrape_id), "pages")

def get_faiss_index_dir(scrape_id: str) -> str:
    """Returns the directory where the FAISS index for a scrape ID is stored."""
    return os.path.join(get_scrape_dir(scrape_id), "faiss_index")

def clean_html_content(soup):
    for tag in soup.find_all(["script", "style", "head", "img", "svg", "link", "aside", "form"]):
        tag.decompose()

    body_content = soup.body
    return body_content if body_content else soup

# Function to create a valid filename
def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text)  # remove non-word characters
    return re.sub(r'[-\s]+', '_', text).strip('_').lower()
