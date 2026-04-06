from app.services.retriever import retrieve_relevant_chunks
from app.services.llm_services import generate_answer_stream_with_groq, contextualize_query
from app.services.firestore_services import get_all_actionable_links
import json


async def answer_user_question_stream(question: str, history: list = None, user_profile: dict = None):
    """
    Full Async RAG pipeline yielding NDJSON chunks:
    history -> contextualize query -> retrieve chunks -> build context -> generate answer streaming
    """
    standalone_query = await contextualize_query(question, history)
    
    chunks = await retrieve_relevant_chunks(standalone_query, limit=15)

    context = ""
    sources = []
    if chunks:
        context = "KNOWLEDGE BASE DOCUMENTS:\n\n" + "\n\n".join(
            [
                f"[Source: {chunk['filename']} | Category: {chunk.get('category', 'General')} | Chunk {chunk['chunk_index']}]\n{chunk['text']}"
                for chunk in chunks
            ]
        ) + "\n\n"

    # Fetch actionable links for possible walkthroughs
    try:
        links = get_all_actionable_links()
        if links:
            context += "AVAILABLE ACTIONABLE LINKS & WALKTHROUGHS:\n"
            for link in links:
                context += f"- Title: {link.get('title')}\n  URL: {link.get('url')}\n  Description: {link.get('description')}\n"
                if link.get("walkthrough"):
                    context += f"  Walkthrough Steps: {json.dumps(link.get('walkthrough'))}\n"
            context += "\n"
    except Exception as e:
        print(f"Failed to fetch actionable links: {e}")

    # Stream the LLM response tokens directly
    async for text_chunk in generate_answer_stream_with_groq(question, context, history, user_profile=user_profile):
        yield json.dumps({"type": "token", "content": text_chunk}) + "\n"
        
    # Finally, signal completion
    yield json.dumps({"type": "done"}) + "\n"