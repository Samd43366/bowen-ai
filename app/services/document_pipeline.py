from app.services.text_splitter import split_text
from app.services.embeddings import embed_texts, embed_texts_sparse
from app.services.qdrant_services import upsert_document_chunks
import traceback
from app.services.firestore_services import update_document_status
from app.services.pdf_services import extract_text_from_pdf
from app.services.word_services import extract_text_from_docx


def process_document(document_id: str, file_name: str, full_text: str, category: str = "Uncategorized") -> dict:
    """
    Process uploaded document:
    - split text
    - embed chunks in batches
    - upload to Qdrant in batches
    - track progress in Firestore
    """
    if not full_text or not full_text.strip():
        return {
            "message": "Uploaded document is empty.",
            "file_name": file_name,
            "chunks_indexed": 0
        }

    chunks = split_text(full_text)

    if not chunks:
        return {
            "message": "No chunks created from document.",
            "file_name": file_name,
            "chunks_indexed": 0
        }

    total_chunks = len(chunks)
    batch_size = 100
    chunks_indexed = 0

    # Initial update to say we found chunks
    update_document_status(document_id, {
        "processed_chunks": 0,
        "total_chunks": total_chunks,
        "status": "processing"
    })

    for i in range(0, total_chunks, batch_size):
        chunk_batch = chunks[i:i + batch_size]
        
        # embed
        batch_embeddings = embed_texts(chunk_batch)
        batch_sparse_embeddings = embed_texts_sparse(chunk_batch)
        
        # upsert
        upsert_document_chunks(
            chunks=chunk_batch,
            embeddings=batch_embeddings,
            sparse_embeddings=batch_sparse_embeddings,
            metadata={"filename": file_name, "category": category}
        )
        
        chunks_indexed += len(chunk_batch)
        
        # update firestore progress
        update_document_status(document_id, {
            "processed_chunks": chunks_indexed,
            "total_chunks": total_chunks,
            "status": "processing"
        })

    return {
        "message": "Document uploaded and indexed successfully.",
        "file_name": file_name,
        "chunks_indexed": chunks_indexed,
        "total_chunks": total_chunks
    }


def process_document_background(document_id: str, file_name: str, full_text: str, category: str = "Uncategorized"):
    try:
        result = process_document(document_id, file_name, full_text, category)
        
        status = "success" if result.get("chunks_indexed", 0) > 0 else "failed"
        update_document_status(document_id, {
            "status": status,
            "chunks_indexed": result.get("chunks_indexed", 0),
            "total_chunks": result.get("total_chunks", 0)
        })
    except Exception as e:
        print(f"Error processing document {file_name}: {e}")
        traceback.print_exc()
        update_document_status(document_id, {
            "status": "failed",
            "error_detail": str(e)
        })