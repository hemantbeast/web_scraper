
# Web Scraping and Q&A Project

This project provides a FastAPI application that can scrape content from a given website (including dynamically loaded content via Selenium and text from PDF documents), store the extracted information locally as a FAISS vector database, and then allow users to query that content using Azure OpenAI's language models.


## Features

- **Comprehensive Web Scraping:** Utilizes Selenium to scrape dynamically loaded content from web pages.
- **PDF Text Extraction**: Downloads and extracts text from PDF documents found during the crawl.
- **Internal Link Crawling:** Recursively discovers and scrapes all internal links within the specified domain.
- **Unique Scrape IDs:** Each scraping operation is assigned a unique UUID, and its data (raw pages and FAISS index) is stored in a dedicated directory.
- **Local Vector Database:** Stores scraped content as vector embeddings using FAISS for efficient similarity search.
- **Azure OpenAI Integration:**
    - Uses `AzureOpenAIEmbeddings` for generating vector embeddings.
    - Uses `AzureChatOpenAI` for answering user queries based on the retrieved content.
- **FastAPI Backend:** Provides a RESTful API for triggering scraping and performing queries.
- **Modular Code:** The scraping and processing logic is broken down into separate, reusable functions.


## Setup

### 1. Clone the repository

Clone or download and extract the zip in your working project directory.

### 2. Install Dependencies

Ensure you have all the necessary Python packages installed. You can install them using `pip` and your `requirements.txt` file, or manually:

```bash
  pip install -r requirements.txt
  # If not in requirements.txt, ensure these are installed:
  pip install selenium pypdf httpx beautifulsoup4 python-dotenv uvicorn langchain-text-splitters langchain-openai langchain-community webdriver-manager
```

### 3. Configure Azure OpenAI Environment Variables

Create a file named `.env` in the same directory as `main.py` and add your Azure OpenAI service details:

```bash
API_KEY="your_azure_openai_api_key"

MODEL_NAME="your-embedding-model-deployment-name" # e.g., text-embedding-ada-002
CHAT_MODEL_NAME="your-chat-model-deployment-name" # e.g., gpt-4o

MODEL_VERSION="2025-07-22"
MODEL_URL="https://your-resource-name.openai.azure.com/"
```

**Important:** Replace the placeholder values with your actual Azure OpenAI credentials and deployment names.

### 4. ChromeDriver Setup

`webdriver-manager` will automatically download the correct ChromeDriver executable for your system when the application runs for the first time. No manual setup is typically required.

## How to Run

1.  **Start the FastAPI application:**

    ```
    uvicorn main:app --reload

    ```

    The application will start on `http://127.0.0.1:8080`. The `--reload` flag is useful for development as it restarts the server on code changes.

## API Endpoints

You can interact with the API using tools like `curl`, Postman, Insomnia, or by opening the URLs directly in your browser.

### 1. Scrape a Website

This endpoint initiates the crawling process for a given URL. It will scrape all internal HTML pages and PDF documents, extract their text, and create a unique FAISS vector database for this scrape operation.

* **Endpoint:** `/scrape`

* **Method:** `GET`

* **Query Parameters:**

    * `url` (string, required): The URL of the website to scrape.

* **Example URL in browser:**
    `http://127.0.0.1:8000/scrape?url=https://www.example.com`

* **Example `curl` command:**

    ```
    curl -X GET "[http://127.0.0.1:8000/scrape?url=https://www.google.com](http://127.0.0.1:8000/scrape?url=https://www.google.com)"

    ```

* **Response:**
    A successful response will return a `scrape_id` which you'll need for querying.

    ```
    {
        "message": "Successfully crawled '[https://www.google.com](https://www.google.com)' and created a new vector store.",
        "scrape_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
    }

    ```

### 2. Query Scraped Content

Once a website has been scraped and its vector database created, you can use this endpoint to ask questions about its content.

* **Endpoint:** `/query`

* **Method:** `GET`

* **Query Parameters:**

    * `scrape_id` (string, required): The unique ID of the scraped website data (obtained from the `/scrape` endpoint).

    * `query` (string, required): The question to ask about the scraped content.

* **Example URL in browser:**
    `http://127.0.0.1:8000/query?scrape_id=THE_UUID_YOU_GOT_FROM_SCRAPE&query=What%20is%20the%20main%20purpose%20of%20this%20website%3F`
    (Remember to URL-encode your query string if typing directly into a browser or using `curl` without `-G` and `data-urlencode`).

* **Example `curl` command:**

    ```
    curl -X GET "[http://127.0.0.1:8000/query?scrape_id=a1b2c3d4-e5f6-7890-1234-567890abcdef&query=What%20are%20the%20contact%20details%3F](http://127.0.0.1:8000/query?scrape_id=a1b2c3d4-e5f6-7890-1234-567890abcdef&query=What%20are%20the%20contact%20details%3F)"

    ```

* **Response:**
    A successful response will return the answer generated by the Azure OpenAI model based on the scraped content.

    ```
    {
        "answer": "The contact details are..."
    }

    ```

## Troubleshooting

* **`ValueError: Azure OpenAI environment variables...`**: Ensure all required Azure OpenAI variables are correctly set in your `.env` file.

* **Selenium Errors (e.g., `WebDriverException`)**:

    * Ensure `webdriver-manager` is installed and has successfully downloaded the ChromeDriver.

    * Check your internet connection.

    * For deployment, ensure your environment has Chrome installed and accessible by Selenium.

* **`FileNotFoundError: FAISS index for scrape_id ... not found`**: You must successfully run the `/scrape` endpoint for a URL before you can query it with its `scrape_id`.

* **`httpx.InvalidURL` or URL resolution issues**: Double-check the URLs you are providing. The `normalize_url` function attempts to handle various formats.

* **No content scraped**: Some websites might have very complex JavaScript rendering or anti-scraping measures. You might need to adjust Selenium's wait conditions or explore other scraping techniques for such sites.
    
## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/hemantbeast/web_scraper/blob/main/LICENSE) file for details.

