from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api.routes import router as api_router, lifespan

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    lifespan=lifespan,
    title="Web Scraper and Q&A API",
    description="API to scrape a website (all internal links with Selenium), store its content as a unique vector database, and answer questions based on it using Azure OpenAI."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api", tags=["Agent"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8080)