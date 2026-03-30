from datetime import datetime, timezone
from firebase_admin import firestore
from app.core.database import db

ANALYTICS_COL = "analytics"

def get_today_id():
    """Returns 'YYYY-MM-DD' representing the current day."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def log_query(answered: bool):
    """
    Increments either the answered_questions or unanswered_questions 
    counter for the current day.
    """
    doc_id = get_today_id()
    doc_ref = db.collection(ANALYTICS_COL).document(doc_id)
    
    field = "answered_questions" if answered else "unanswered_questions"
    
    try:
        doc_ref.update({
            field: firestore.Increment(1)
        })
    except Exception:
        # Document might not exist yet today, initialize it safely.
        doc_ref.set({
            "answered_questions": 1 if answered else 0,
            "unanswered_questions": 0 if answered else 1,
            "active_users": []
        }, merge=True)

def log_user_activity(email: str):
    """
    Maintains a unique list of emails active today, representing Daily Active Users (DAU).
    """
    if not email:
        return
        
    doc_id = get_today_id()
    doc_ref = db.collection(ANALYTICS_COL).document(doc_id)
    
    try:
        doc_ref.update({
            "active_users": firestore.ArrayUnion([email])
        })
    except Exception:
        doc_ref.set({
            "answered_questions": 0,
            "unanswered_questions": 0,
            "active_users": [email]
        }, merge=True)

async def log_unanswered_question(question: str):
    """
    Categorizes the question using LLM and logs it to Firestore.
    """
    from app.services.llm_services import get_groq_client
    from app.core.config import settings
    
    # 1. Categorize using a quick LLM call
    categories = ["Admissions", "Fees & Finance", "Accommodation", "Academic Rules", "Departmental/Faculty", "General School Info", "Other"]
    prompt = f"""
    Categorize the following user question into exactly ONE of these categories: 
    {', '.join(categories)}
    
    Question: {question}
    
    Respond only with the category name.
    """
    
    category = "General School Info" # Default
    try:
        client = get_groq_client()
        resp = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=20
        )
        category = resp.choices[0].message.content.strip()
        # Clean up in case of hallucinated formatting
        if category not in categories:
            # Try to see if it's contained within the response
            for c in categories:
                if c.lower() in category.lower():
                    category = c
                    break
            else:
                category = "General School Info"
    except Exception as e:
        print(f"Failed to categorize question: {e}")

    # 2. Log to Firestore
    # Use a hashed version of the question or the question itself as doc ID to increment counts
    import hashlib
    q_hash = hashlib.md5(question.strip().lower().encode()).hexdigest()
    
    doc_ref = db.collection("unanswered_questions").document(q_hash)
    
    try:
        doc_ref.update({
            "count": firestore.Increment(1),
            "last_asked": datetime.now(timezone.utc)
        })
    except Exception:
        doc_ref.set({
            "question": question,
            "category": category,
            "count": 1,
            "first_asked": datetime.now(timezone.utc),
            "last_asked": datetime.now(timezone.utc)
        })
