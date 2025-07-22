import os
import uuid
from contextlib import asynccontextmanager

from fastapi import APIRouter, Query, HTTPException, FastAPI
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

from scraper.page_scraper import crawl_website
from utils.page_utils import BASE_SCRAPED_DATA_DIR
from vectorstore.embedding import load_vector_store, create_and_save_vector_store

router = APIRouter()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for managing the lifespan of the FastAPI application.
    Ensures the base scraped data directory exists on startup.
    """
    os.makedirs(BASE_SCRAPED_DATA_DIR, exist_ok=True)
    print(f"Base scraped data directory '{BASE_SCRAPED_DATA_DIR}' ensured to exist.")

    yield # Application starts here
    # Code after yield will run on shutdown (e.g., for cleanup)
    print("FastAPI application shutting down.")

@router.get("/scrape", summary="Scrape a website (all internal links) and create a unique local vector store")
async def scrape_website(url: str = Query(
    ...,
    examples=["https://www.google.com"]
)):
    """
    Initiate the web scraping process for a given URL.
    The scraped content is processed, embedded, and stored in a local FAISS vector database.
    """
    if not url:
        raise HTTPException(status_code=400, detail="'url' field is required in the request body.")

    # Generate a unique UUID for this scraping operation
    scrape_id = str(uuid.uuid4())
    print(f"Received request to scrape: {url}. Assigned scrape_id: {scrape_id}")

    try:
        # Step 1: Scrape and process the website content using Selenium
        texts = await crawl_website(url, scrape_id)

        if not texts:
            raise HTTPException(status_code=500,
                                detail="No content was scraped from the provided URL or its internal links.")

        # Step 2: Create and save the vector store from the processed text chunks
        await create_and_save_vector_store(texts, scrape_id)

        return {"message": f"Successfully crawled '{url}' and created a new vector store.", "scrape_id": scrape_id}
    except Exception as e:
        # Catch any exception during the process and return an appropriate HTTP error
        raise HTTPException(status_code=500, detail=f"Failed to scrape and process website: {e}")

@router.get("/query", summary="Query the scraped website content using a specific scrape ID")
async def answer_query_endpoint(
        query: str = Query(
            ...,
            examples=["What is the main topic of this website?"]
        ),
        scrape_id: str = Query(
            ...,
            examples=["d3478378abe3448cda"]
        )):
    """
    Endpoint to answer questions based on the locally stored vector database
    of the previously scraped website.
    """
    if not scrape_id:
        raise HTTPException(status_code=400, detail="'scrape_id' field is required in the request body.")
    if not query:
        raise HTTPException(status_code=400, detail="'query' field is required in the request body.")

    print(f"Received query: '{query}' for scrape_id: {scrape_id}")
    try:
        # Load the specific vector store for the given scrape_id
        current_vector_store = await load_vector_store(scrape_id)

        # Step 1: Retrieve relevant documents (text chunks) from the vector store
        retriever = current_vector_store.as_retriever()
        docs = await retriever.ainvoke(query)

        # Combine the content of the retrieved documents to form the context for the LLM
        context_text = "\n\n".join([doc.page_content for doc in docs])
        print(f"Retrieved {len(docs)} relevant document(s) for scrape_id {scrape_id}.")

        # Ensure OpenAI API key is available for the LLM call
        api_key = os.getenv("CHAT_MODEL_KEY")
        if not api_key:
            raise ValueError("API_KEY environment variable not set for LLM.")

        # Step 2: Initialize the ChatOpenAI model
        # Using "o4-mini" as a common and cost-effective model.
        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("CHAT_MODEL_NAME"),
            azure_endpoint=os.getenv("CHAT_MODEL_URL"),
            api_key=SecretStr(api_key),
            api_version=os.getenv("CHAT_MODEL_VERSION"),
            model="o4-mini",
            temperature=0.7
        )

        # Step 3: Define the prompt template for the LLM
        # This template guides the LLM on how to use the provided context and answer the question.
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "You are an AI assistant tasked with answering questions based ONLY on the provided context. "
                           "If the answer is not explicitly available in the context, state that you don't have enough information. "
                           "Do not make up information."),
                ("human", "Context: {context}\n\nQuestion: {query}"),
            ]
        )

        # Step 4: Create a LangChain chain to combine prompt and LLM
        # The chain pipes the output of the prompt template into the LLM.
        chain = prompt_template | llm

        # Step 5: Invoke the chain to get the answer from the LLM
        response = await chain.ainvoke({"context": context_text, "query": query})

        return {"answer": response.content}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Scraped data for ID '{scrape_id}' not found. Please scrape it first. Error: {e}")
    except Exception as e:
        print(f"Error during query operation for scrape_id {scrape_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {e}")
