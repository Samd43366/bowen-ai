from app.services.retriever import retrieve_relevant_chunks
from app.services.llm_services import generate_answer_stream_with_groq, contextualize_query
import json


async def answer_user_question_stream(question: str, history: list = None):
    """
    Full Async RAG pipeline yielding NDJSON chunks:
    history -> contextualize query -> retrieve chunks -> build context -> generate answer streaming
    """
    standalone_query = await contextualize_query(question, history)
    
    chunks = await retrieve_relevant_chunks(standalone_query, limit=5)

    context = ""
    sources = []
    if chunks:
        context = "\n\n".join(
            [
                f"[Source: {chunk['filename']} | Chunk {chunk['chunk_index']}]\n{chunk['text']}"
                for chunk in chunks
            ]
        )

    # Stream the LLM response tokens directly
    async for text_chunk in generate_answer_stream_with_groq(question, context, history):
        yield json.dumps({"type": "token", "content": text_chunk}) + "\n"
        
    # Finally, signal completion
    yield json.dumps({"type": "done"}) + "\n"