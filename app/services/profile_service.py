from app.services.llm_services import get_groq_client
from app.core.config import settings
from app.services.firestore_services import update_user
import json
import asyncio

async def extract_and_update_profile(email: str, question: str, answer: str, current_profile: dict):
    """
    Background task to extract user information from the conversation and update Firestore.
    """
    client = get_groq_client()
    
    # Skip for guests
    if email == "guest":
        return

    system_prompt = """
You are an expert at extracting user profile information from a conversation.
Your goal is to identify and extract traits like:
- Role (Student, Student Union, School Official, Parent)
- Level (e.g., 100L, 200L, etc.)
- Hostel (e.g., Ebenezer, Luke, etc.)
- Department/Course
- Any other relevant personal preferences or academic details.

Given the current user profile, a user's question, and the assistant's answer, output a JSON object of NEW or UPDATED information.
Only include information that is EXPLICITLY stated or STRONGLY implied.
If no new information is found, output an empty JSON object {}.

CURRENT PROFILE:
{current_profile}

OUTPUT FORMAT:
{
  "role": "...",
  "level": "...",
  "hostel": "...",
  "metadata": {
    "department": "...",
    "interests": "...",
    ...
  }
}
"""
    
    prompt = f"User Question: {question}\n\nAssistant Answer: {answer}\n\nExtracted Info (JSON):"
    
    try:
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt.format(current_profile=json.dumps(current_profile))},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        extracted_data = json.loads(response.choices[0].message.content)
        if not extracted_data:
            return

        # Prepare updates
        updates = {}
        if "role" in extracted_data: updates["role"] = extracted_data["role"]
        if "level" in extracted_data: updates["level"] = extracted_data["level"]
        if "hostel" in extracted_data: updates["hostel"] = extracted_data["hostel"]
        
        # Merge metadata
        if "metadata" in extracted_data:
            existing_metadata = current_profile.get("metadata", {})
            if isinstance(existing_metadata, dict):
                existing_metadata.update(extracted_data["metadata"])
                updates["metadata"] = existing_metadata
            else:
                updates["metadata"] = extracted_data["metadata"]

        if updates:
            # Run the update in Firestore
            update_user(email, updates)
            print(f"Updated profile for {email}: {updates}")
            
    except Exception as e:
        print(f"Failed to extract profile info: {e}")
