from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes import router
from backend.app.database.connection import init_db
from backend.app.core.config import settings
from backend.app.core.logging import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure SQLite tables and WAL mode are initialized
    logger.info("Starting up FastAPI application...")
    init_db()
    logger.info(f"Connected to Groq (Key: {settings.get_redacted_groq_key()}, Model: {settings.GROQ_MODEL})")
    yield
    # Shutdown
    logger.info("Shutting down FastAPI application.")

app = FastAPI(
    title="Agentic Content Evaluator — Self-Evaluating Lesson Pipeline",
    description="Agentic learning content generation with LangGraph, Groq, hybrid evaluation, and persistent memory.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Mount frontend production build if available
from pathlib import Path
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info(f"Mounted frontend production build from {frontend_dist}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
