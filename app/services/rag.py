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
    
    chunks = await retrieve_relevant_chunks(standalone_query, limit=8)

    context = ""
    if chunks:
        unique_sources = set()
        for chunk in chunks:
            unique_sources.add(chunk['filename'])
            
        context = "KNOWLEDGE BASE DOCUMENTS:\n\n" + "\n\n".join(
            [
                f"[Source: {chunk['filename']} | Category: {chunk.get('category', 'General')} | Chunk {chunk['chunk_index']}]\n{chunk['text']}"
                for chunk in chunks
            ]
        ) + "\n\n"
        
        # Emit the sources event first so UI can display them
        yield json.dumps({"type": "sources", "data": list(unique_sources)}) + "\n"

    # Fetch relevant actionable links for possible walkthroughs
    try:
        all_links = get_all_actionable_links()
        query_lower = standalone_query.lower()
        if all_links:
            # Simple keyword filtering for relevance
            relevant_links = []
            for link in all_links:
                title = link.get('title', '').lower()
                desc = link.get('description', '').lower()
                # If query contains link keywords or vice versa
                if any(word in query_lower for word in title.split()) or \
                   any(word in query_lower for word in desc.split()) or \
                   (len(all_links) < 3): # Always show a few if list is very small
                    relevant_links.append(link)
            
            if relevant_links:
                context += "RELEVANT ACTIONABLE LINKS & WALKTHROUGHS:\n"
                for link in relevant_links:
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