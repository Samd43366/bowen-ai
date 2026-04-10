import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, SparseVectorParams, SparseVector, Prefetch, FusionQuery, Fusion
from app.core.config import settings

_qdrant_client = None


def get_qdrant_client():
    """
    Create and cache Qdrant client once.
    """
    global _qdrant_client

    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=60
        )

    return _qdrant_client


def ensure_collection_exists(vector_size: int = 384):
    """
    Create collection if it doesn't exist.
    all-MiniLM-L6-v2 = 384 dimensions
    """
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION_NAME

    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if collection_name not in existing_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config={"dense": VectorParams(size=vector_size, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams()}
        )


def upsert_document_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    sparse_embeddings: list[dict],
    metadata: dict
) -> int:
    """
    Store document chunks in Qdrant.
    """
    if not chunks or not embeddings or not sparse_embeddings or len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings must exist and have same length.")

    ensure_collection_exists(vector_size=len(embeddings[0]))

    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION_NAME

    points = []

    for i, (chunk, vector, sparse_vec) in enumerate(zip(chunks, embeddings, sparse_embeddings)):
        payload = {
            "text": chunk,
            "filename": metadata.get("filename", "unknown"),
            "chunk_index": i
        }

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": vector,
                    "sparse": SparseVector(
                        indices=sparse_vec["indices"],
                        values=sparse_vec["values"]
                    )
                },
                payload=payload
            )
        )

    client.upsert(
        collection_name=collection_name,
        points=points
    )

    return len(points)


def search_document_chunks(query_vector: list[float], query_sparse: dict, limit: int = 5) -> list:
    """
    Hybrid Search similar chunks in Qdrant.
    """
    client = get_qdrant_client()

    results = client.query_points(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        prefetch=[
            Prefetch(
                query=query_vector,
                using="dense",
                limit=limit * 2
            ),
            Prefetch(
                query=SparseVector(
                    indices=query_sparse["indices"],
                    values=query_sparse["values"]
                ),
                using="sparse",
                limit=limit * 2
            )
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit
    )

    return results.points if hasattr(results, "points") else []


def delete_document_chunks(filename: str):
    """
    Deletes all chunks in Qdrant matching the exact filename.
    """
    client = get_qdrant_client()
    
    try:
        client.create_payload_index(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            field_name="filename",
            field_schema="keyword"
        )
    except Exception:
        pass
        
    client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="filename",
                    match=MatchValue(value=filename)
                )
            ]
        )
    )


def get_document_preview_chunks(filename: str, limit: int = 5) -> list:
    """
    Retrieve a few sample chunks for a specific document filename.
    """
    client = get_qdrant_client()
    try:
        results, next_page_offset = client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="filename",
                        match=MatchValue(value=filename)
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        # Sort by chunk_index
        chunks = [{"chunk_index": r.payload.get("chunk_index"), "text": r.payload.get("text")} for r in results]
        chunks.sort(key=lambda x: x["chunk_index"] if x["chunk_index"] is not None else 0)
        return chunks
    except Exception as e:
        print(f"Error fetching preview chunks: {e}")
        return []