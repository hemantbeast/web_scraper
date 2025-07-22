import asyncio
import os
import uuid
from collections import deque
from urllib.parse import urlparse

import html2text
import httpx
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.page_utils import get_pages_dir, clean_html_content, slugify
from utils.url_utils import get_domain, normalize_url, extract_text_from_pdf_url
from utils.web_driver_utils import get_web_driver


def _scrape_html_page(driver, url: str) -> BeautifulSoup | None:
    """
    Fetches the fully rendered HTML content of a single page using Selenium
    and returns a BeautifulSoup object. This is a synchronous function.
    """
    try:
        driver.get(url)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        html_content = driver.page_source
        return BeautifulSoup(html_content, 'html.parser')

    except Exception as e:
        print(f"Error scraping HTML page {url} with Selenium: {e}")
        return None


def _extract_text_from_html(soup: BeautifulSoup) -> str:
    """
    Extracts text content from the entire body of a BeautifulSoup object.
    """
    if not soup or not soup.body:
        return ""

    main_content_element = clean_html_content(soup)

    if not main_content_element:
        return ""

    return html2text.html2text(str(soup.body))


def _process_content_and_store(url: str, markdown: str, scrape_id: str, text_splitter: RecursiveCharacterTextSplitter,
                               all_scraped_texts: list, soup: BeautifulSoup):
    """
    Splits text content into chunks, adds to the main list, and saves to a local file.
    """
    if not markdown.strip():
        print(f"No meaningful text extracted from {url}. Skipping for embedding.")
        return

    chunks = text_splitter.split_text(markdown)
    all_scraped_texts.extend(chunks)

    # Generate filename based on title or URL
    title_tag = soup.title.string.strip() if soup.title else ''

    if title_tag:
        filename_base = slugify(title_tag)
    else:
        parsed_url = urlparse(url)
        filename_base = slugify(parsed_url.path or parsed_url.netloc)

    if not filename_base:
        unique_id = str(uuid.uuid4())
        filename_base = unique_id

    pages_dir = get_pages_dir(scrape_id)
    page_filename = os.path.join(pages_dir, f"{filename_base}.md")

    with open(page_filename, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"Saved content for {url} to {page_filename}")


def _extract_and_queue_links(soup: BeautifulSoup, current_url: str, base_domain: str, visited_urls: set,
                             urls_to_visit: deque):
    """
    Extracts internal links from a BeautifulSoup object and adds them to the queue if not visited.
    """
    if not soup:
        return

    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url_obj = httpx.URL(current_url).join(href)
        full_url = str(full_url_obj)

        normalized_full_url = normalize_url(full_url)

        if get_domain(normalized_full_url) == base_domain and normalized_full_url not in visited_urls:
            urls_to_visit.append(normalized_full_url)


async def crawl_website(start_url: str, scrape_id: str) -> list[str]:
    """
    Crawls the website starting from start_url, scrapes all internal links,
    stores content locally, and returns a list of all scraped texts.
    Handles both HTML and PDF content.
    """
    pages_dir = get_pages_dir(scrape_id)
    os.makedirs(pages_dir, exist_ok=True)

    base_domain = get_domain(start_url)
    visited_urls = set()
    urls_to_visit = deque([start_url])
    all_scraped_texts = []

    driver = None

    try:
        driver = get_web_driver()

        print(f"Starting crawl for scrape_id: {scrape_id} from {start_url}")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

        # List of non-textual file extensions to explicitly skip
        # PDFs are now handled, so removed from this list
        media_extensions_to_skip = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
            '.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv',
            '.mp3', '.wav', '.ogg', '.webm',
            '.ico', '.zip', '.rar', '.tar', '.gz', '.doc', '.docx', '.ppt', '.xls'
        ]

        while urls_to_visit:
            current_url = urls_to_visit.popleft()
            normalized_current_url = normalize_url(current_url)

            if normalized_current_url in visited_urls:
                continue

            print(f"\nScraping: {current_url}")
            visited_urls.add(normalized_current_url)

            markdown = ""
            soup = None

            # Determine content type based on extension
            if normalized_current_url.lower().endswith('.pdf'):
                print(f"Processing PDF document: {normalized_current_url}")
                markdown = await extract_text_from_pdf_url(normalized_current_url)

            elif any(normalized_current_url.lower().endswith(ext) for ext in media_extensions_to_skip):
                print(f"Skipping non-textual binary document: {normalized_current_url}")
                continue  # Skip to next URL in queue

            else:
                # Assume HTML content for other URLs
                soup = await asyncio.to_thread(_scrape_html_page, driver, current_url)

                if not soup:
                    print(f"Skipping empty content for {current_url}")
                    continue

                markdown = _extract_text_from_html(soup)

            if not markdown.strip():
                print(f"No meaningful text extracted from {current_url}. Skipping for embedding.")
                continue

            _process_content_and_store(current_url, markdown, scrape_id, text_splitter, all_scraped_texts, soup)

            # Extract links only from HTML pages (PDFs don't have navigable links in this context)
            if soup:
                _extract_and_queue_links(soup, current_url, base_domain, visited_urls, urls_to_visit)

        print(f"\nFinished crawling. Scraped {len(all_scraped_texts)} pages.")
        return all_scraped_texts

    except Exception as e:
        print(f"An error occurred during crawling: {e}")
        raise

    finally:
        # Ensure the browser is closed even if an error occurs
        if driver:
            driver.quit()
            print("Selenium WebDriver closed after crawling.")
