"""Knowledge base ingestion, vector indexing, and semantic retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from google import genai
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from src.config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    EMBEDDING_MODEL,
    EMBEDDING_MODEL_FALLBACKS,
    TOP_K,
    require_gemini_api_key,
)
from src.retry import call_with_backoff


RETRIEVAL_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "for",
    "how",
    "i",
    "is",
    "it",
    "me",
    "my",
    "not",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "what",
    "why",
    "with",
    "work",
    "well",
    "you",
    "your",
}


@dataclass(frozen=True)
class LoadedDocument:
    """Parsed document text with file metadata preserved for attribution."""

    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RetrievedChunk:
    """Single retrieved Chroma result normalized for generation and UI display."""

    text: str
    source: str
    score: float
    metadata: dict[str, Any]


def get_gemini_client() -> genai.Client:
    """Create a Gemini client using the configured API key."""
    return genai.Client(api_key=require_gemini_api_key())


def load_documents(data_dir: Path = DATA_DIR) -> list[LoadedDocument]:
    """Load supported knowledge base files with source metadata."""
    documents: list[LoadedDocument] = []
    if not data_dir.exists():
        return documents

    for path in sorted(data_dir.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".md":
            documents.append(_load_text_file(path, "md"))
        elif suffix == ".txt":
            documents.append(_load_text_file(path, "txt"))
        elif suffix == ".pdf":
            documents.extend(_load_pdf_file(path))
    return [doc for doc in documents if doc.text.strip()]


def _load_text_file(path: Path, file_type: str) -> LoadedDocument:
    """Read a Markdown or plain-text knowledge base file."""
    return LoadedDocument(
        text=path.read_text(encoding="utf-8"),
        metadata={
            "source": path.name,
            "file_type": file_type,
            "page_number": 0,
            "document_path": str(path),
        },
    )


def _load_pdf_file(path: Path) -> list[LoadedDocument]:
    """Extract PDF text page by page so page metadata remains available."""
    reader = PdfReader(str(path))
    documents: list[LoadedDocument] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        documents.append(
            LoadedDocument(
                text=text,
                metadata={
                    "source": path.name,
                    "file_type": "pdf",
                    "page_number": page_index,
                    "document_path": str(path),
                },
            )
        )
    return documents


def chunk_documents(documents: list[LoadedDocument]) -> list[LoadedDocument]:
    """Split documents into retrieval-sized chunks while preserving metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks: list[LoadedDocument] = []
    for document in documents:
        parts = splitter.split_text(document.text)
        for chunk_index, text in enumerate(parts):
            metadata = dict(document.metadata)
            metadata["chunk_index"] = chunk_index
            chunks.append(LoadedDocument(text=text, metadata=metadata))
    return chunks


def embed_texts(texts: list[str], client: genai.Client | None = None) -> list[list[float]]:
    """Embed text with Gemini, trying configured fallbacks for API compatibility."""
    if not texts:
        return []
    active_client = client or get_gemini_client()
    last_error: Exception | None = None
    for model_name in EMBEDDING_MODEL_FALLBACKS:
        try:
            response = call_with_backoff(
                lambda: active_client.models.embed_content(
                    model=model_name,
                    contents=texts,
                )
            )
            return _extract_embedding_vectors(response, len(texts))
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Gemini embedding failed for configured models. Last error: {last_error}") from last_error


def _extract_embedding_vectors(response: object, expected_count: int) -> list[list[float]]:
    """Normalize Gemini embedding responses across SDK/model variants."""
    embeddings = getattr(response, "embeddings", None)
    if embeddings is None:
        single_embedding = getattr(response, "embedding", None)
        embeddings = [single_embedding] if single_embedding is not None else []
    vectors: list[list[float]] = []
    for item in embeddings:
        values = getattr(item, "values", None)
        if values is None and isinstance(item, dict):
            values = item.get("values")
        if values is None:
            raise RuntimeError("Gemini embedding response did not include vector values.")
        vectors.append([float(value) for value in values])
    if len(vectors) != expected_count:
        raise RuntimeError("Gemini embedding response count did not match input count.")
    return vectors


def get_collection() -> chromadb.Collection:
    """Return the persistent cosine-similarity ChromaDB collection."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def stable_chunk_id(chunk: LoadedDocument) -> str:
    """Build a deterministic chunk ID to avoid duplicate Chroma inserts."""
    metadata = chunk.metadata
    key = f"{metadata['document_path']}|{metadata.get('page_number', 0)}|{metadata['chunk_index']}"
    return key.replace("\\", "/")


def index_documents() -> int:
    """Index only missing chunks, returning the number of newly added chunks."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    if not chunks:
        return 0

    collection = get_collection()
    ids = [stable_chunk_id(chunk) for chunk in chunks]
    existing = collection.get(ids=ids)
    existing_ids = set(existing.get("ids", []))
    new_chunks = [(chunk_id, chunk) for chunk_id, chunk in zip(ids, chunks) if chunk_id not in existing_ids]
    if not new_chunks:
        return 0

    new_ids = [chunk_id for chunk_id, _ in new_chunks]
    texts = [chunk.text for _, chunk in new_chunks]
    metadatas = [_chroma_metadata(chunk.metadata) for _, chunk in new_chunks]
    embeddings = embed_texts(texts)
    collection.add(ids=new_ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
    return len(new_chunks)


def retrieve(query: str, top_k: int = TOP_K) -> tuple[list[RetrievedChunk], float]:
    """Retrieve top-k chunks and return an adjusted confidence score."""
    collection = get_collection()
    query_embedding = embed_texts([query])[0]
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    chunks: list[RetrievedChunk] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        score = max(0.0, min(1.0, 1.0 - float(distance)))
        chunks.append(
            RetrievedChunk(
                text=text,
                source=str(metadata.get("source", "")),
                score=score,
                metadata=dict(metadata),
            )
        )
    best_confidence = _adjust_confidence_for_query_overlap(query, chunks)
    return chunks, best_confidence


def unique_sources(chunks: list[RetrievedChunk]) -> list[str]:
    """Return source file names once, preserving retrieval order."""
    sources: list[str] = []
    for chunk in chunks:
        if chunk.source and chunk.source not in sources:
            sources.append(chunk.source)
    return sources


def _chroma_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Convert metadata to scalar values accepted by ChromaDB."""
    normalized: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            normalized[key] = 0
        elif isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        else:
            normalized[key] = str(value)
    return normalized


def _adjust_confidence_for_query_overlap(query: str, chunks: list[RetrievedChunk]) -> float:
    """Cap confidence for vague or off-topic queries despite vector similarity."""
    if not chunks:
        return 0.0
    best_similarity = max(chunk.score for chunk in chunks)
    query_terms = _meaningful_terms(query)
    if not query_terms:
        return min(best_similarity, 0.44)

    retrieved_text = " ".join(chunk.text.lower() for chunk in chunks)
    matched_terms = {term for term in query_terms if term in retrieved_text}
    overlap_ratio = len(matched_terms) / len(query_terms)
    if overlap_ratio < 0.25:
        return min(best_similarity, 0.44)
    return best_similarity


def _meaningful_terms(text: str) -> set[str]:
    """Extract simple lexical terms for the retrieval-confidence guard."""
    terms = set()
    current = []
    for character in text.lower():
        if character.isalnum():
            current.append(character)
        elif current:
            term = "".join(current)
            if len(term) > 2 and term not in RETRIEVAL_STOPWORDS:
                terms.add(term)
            current = []
    if current:
        term = "".join(current)
        if len(term) > 2 and term not in RETRIEVAL_STOPWORDS:
            terms.add(term)
    return terms


def main() -> None:
    indexed_count = index_documents()
    print(f"Indexed {indexed_count} new chunk(s) into {COLLECTION_NAME}.")


if __name__ == "__main__":
    main()
