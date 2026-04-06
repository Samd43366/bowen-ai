from app.services.embeddings import embed_text, embed_text_sparse
from app.services.qdrant_services import search_document_chunks
import asyncio


async def retrieve_relevant_chunks(question: str, limit: int = 5) -> list[dict]:
    """
    Retrieve relevant document chunks for a user question (Async).
    """
    # Run heavy CPU tasks in a thread pool to avoid blocking FastAPI
    query_vector = await asyncio.to_thread(embed_text, question)
    query_sparse = await asyncio.to_thread(embed_text_sparse, question)

    # Qdrant client is currently sync but fast; we'll run it in thread too for safety
    results = await asyncio.to_thread(search_document_chunks, query_vector, query_sparse, limit=limit)

    chunks = []

    for point in results:
        payload = point.payload or {}

        chunks.append({
            "filename": payload.get("filename", "unknown"),
            "category": payload.get("category", "General"),
            "chunk_index": payload.get("chunk_index", -1),
            "text": payload.get("text", ""),
            "score": getattr(point, "score", None)
        })

    return chunks