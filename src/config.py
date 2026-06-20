"""Central configuration for paths, retrieval settings, and Gemini models."""

from pathlib import Path

from dotenv import load_dotenv
import os


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "support_kb"

# Retrieval settings mirror the source document guidance: focused chunks,
# small overlap, and three best-matching chunks per customer query.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
LOW_CONFIDENCE_THRESHOLD = 0.45

# Order text models by the available quota profile for interactive use.
# The first model handles normal traffic; later models are fallbacks only.
PERSONA_MODEL = "gemini-3.1-flash-lite-preview"
RESPONSE_MODEL = "gemini-3.1-flash-lite-preview"
MAX_OUTPUT_TOKENS = 350
CLASSIFICATION_MAX_OUTPUT_TOKENS = 120
GENERATION_TEMPERATURE = 0.2
CLASSIFICATION_TEMPERATURE = 0.0

PERSONA_MODEL_FALLBACKS = (
    PERSONA_MODEL,
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
)
RESPONSE_MODEL_FALLBACKS = (
    RESPONSE_MODEL,
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
)

# Backward-compatible alias for tests or scripts that import the older name.
GENERATION_MODEL_FALLBACKS = RESPONSE_MODEL_FALLBACKS

# Keep the same embedding model used to build the existing Chroma index.
# Switching embedding models requires rebuilding the vector database.
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_MODEL_FALLBACKS = (
    EMBEDDING_MODEL,
    "text-embedding-004",
)

ALLOWED_PERSONAS = (
    "Technical Expert",
    "Frustrated User",
    "Business Executive",
)

load_dotenv(PROJECT_ROOT / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def require_gemini_api_key() -> str:
    """Return the Gemini API key or raise a clear setup error."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise RuntimeError("GEMINI_API_KEY is not configured. Add it to .env or deployment secrets.")
    return GEMINI_API_KEY
