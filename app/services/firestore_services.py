from datetime import datetime, timezone
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from app.core.database import db

USERS_COLLECTION = "users"

def _scrub_user_data(user_data: dict) -> dict:
    """
    Remove sensitive fields from user data before returning to the application layers.
    """
    if not user_data:
        return None
    sensitive_fields = ["password", "otp_code", "otp_expires_at"]
    for field in sensitive_fields:
        user_data.pop(field, None)
    return user_data

async def get_user_by_email(email: str, scrub: bool = True):
    docs = db.collection(USERS_COLLECTION).where(filter=FieldFilter("email", "==", email)).limit(1).stream()
    users = list(docs)
    if not users:
        return None
    user_doc = users[0]
    user_data = user_doc.to_dict()
    user_data["id"] = user_doc.id
    return _scrub_user_data(user_data) if scrub else user_data

async def get_user_by_matric(matric_number: str, scrub: bool = True):
    docs = db.collection(USERS_COLLECTION).where(filter=FieldFilter("matric_number", "==", matric_number)).limit(1).stream()
    users = list(docs)
    if not users:
        return None
    user_doc = users[0]
    user_data = user_doc.to_dict()
    user_data["id"] = user_doc.id
    return _scrub_user_data(user_data) if scrub else user_data

async def get_user_by_id(user_id: str, scrub: bool = True):
    doc_ref = db.collection(USERS_COLLECTION).document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None
    user_data = doc.to_dict()
    user_data["id"] = doc.id
    return _scrub_user_data(user_data) if scrub else user_data

async def create_user(user_data: dict):
    if "created_at" not in user_data:
        user_data["created_at"] = datetime.now(timezone.utc)
    doc_ref = db.collection(USERS_COLLECTION).document(user_data["email"])
    doc_ref.set(user_data)
    user_data["id"] = doc_ref.id
    return user_data

def delete_user(email: str):
    db.collection(USERS_COLLECTION).document(email).delete()

def update_user(email: str, data: dict):
    db.collection(USERS_COLLECTION).document(email).update(data)

def verify_user(email: str):
    db.collection(USERS_COLLECTION).document(email).update({
        "is_verified": True,
        "otp_code": None,
        "otp_expires_at": None,
        "verified_at": datetime.now(timezone.utc)
    })

def save_user_otp(email: str, otp_code: str, otp_expires_at):
    db.collection(USERS_COLLECTION).document(email).update({
        "otp_code": otp_code,
        "otp_expires_at": otp_expires_at
    })

def approve_admin(email: str):
    db.collection(USERS_COLLECTION).document(email).update({
        "is_approved": True
    })

def get_all_users(scrub: bool = True):
    docs = db.collection(USERS_COLLECTION).stream()
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if scrub:
            _scrub_user_data(data)
        result.append(data)
    return result

# --- DOCUMENT METADATA & CATEGORIES ---

def add_category(name: str):
    doc_ref = db.collection("document_categories").document(name)
    doc_ref.set({"name": name, "created_at": datetime.utcnow().isoformat()})

def get_all_categories():
    docs = db.collection("document_categories").stream()
    return [doc.id for doc in docs]

def delete_category(name: str):
    db.collection("document_categories").document(name).delete()

def get_document_count_by_category(category: str):
    docs = db.collection("documents").where(filter=FieldFilter("category", "==", category)).stream()
    return len(list(docs))

def save_document_metadata(document_data: dict):
    doc_ref = db.collection("documents").document()
    document_data["id"] = doc_ref.id
    document_data["created_at"] = datetime.utcnow().isoformat()
    if "category" not in document_data:
        document_data["category"] = "Uncategorized"
    doc_ref.set(document_data)
    return document_data

def update_document_status(document_id: str, updates: dict):
    updates["updated_at"] = datetime.utcnow().isoformat()
    db.collection("documents").document(document_id).update(updates)

def get_document_by_id(document_id: str):
    doc = db.collection("documents").document(document_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None

def get_all_documents():
    docs = db.collection("documents").stream()
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        result.append(data)
    return result

def delete_document_by_filename(filename: str):
    docs = db.collection("documents").where(filter=FieldFilter("filename", "==", filename)).stream()
    for doc in docs:
        doc.reference.delete()

# --- CHAT SESSIONS ---

def delete_chat_session(session_id: str):
    db.collection("chat_sessions").document(session_id).delete()

def create_chat_session(user_id: str, title: str):
    # Strict Memory Optimization: Enforce Max 5 Sessions Per User
    existing_sessions = get_user_chat_sessions(user_id)
    if len(existing_sessions) >= 5:
        # Keep only the 4 newest, delete the rest so adding this new one makes exactly 5
        for old_session in existing_sessions[4:]:
            delete_chat_session(old_session["id"])

    doc_ref = db.collection("chat_sessions").document()
    session_data = {
        "user_id": user_id,
        "title": title,
        "messages": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    doc_ref.set(session_data)
    session_data["id"] = doc_ref.id
    return session_data

def get_user_chat_sessions(user_id: str):
    # Removing order_by from the query to avoid requiring a composite index.
    # We will sort the results in memory instead.
    docs = db.collection("chat_sessions").where(filter=FieldFilter("user_id", "==", user_id)).stream()
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        result.append(data)
    
    # Sort by updated_at descending
    result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return result

def get_chat_session(session_id: str):
    doc = db.collection("chat_sessions").document(session_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None

def add_message_to_session(session_id: str, role: str, content: str):
    doc_ref = db.collection("chat_sessions").document(session_id)
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    doc_ref.update({
        "messages": firestore.ArrayUnion([message]),
        "updated_at": datetime.utcnow().isoformat()
    })
    return message

# --- AUDIT LOGS ---

def log_admin_action(admin_email: str, action: str, target: str = None):
    doc_ref = db.collection("audit_logs").document()
    doc_ref.set({
        "admin_email": admin_email,
        "action": action,
        "target": target,
        "timestamp": datetime.now(timezone.utc)
    })

def get_recent_audit_logs(limit: int = 50):
    # Note: Requires index on audit_logs [timestamp DESC]
    # We will try a simple stream if index not yet built
    try:
        docs = db.collection("audit_logs").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
        result = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            result.append(data)
        return result
    except:
        # Fallback if index isn't ready
        docs = db.collection("audit_logs").limit(limit).stream()
        result = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            result.append(data)
        # Sort in memory
        result.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
        return result

# --- ACTIONABLE LINKS ---

def save_actionable_link(link_data: dict):
    doc_ref = db.collection("actionable_links").document()
    link_data["id"] = doc_ref.id
    link_data["created_at"] = datetime.now(timezone.utc).isoformat()
    link_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    doc_ref.set(link_data)
    return link_data

def get_all_actionable_links():
    docs = db.collection("actionable_links").stream()
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        result.append(data)
    return result

def get_actionable_link_by_id(link_id: str):
    doc = db.collection("actionable_links").document(link_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None

def update_actionable_link(link_id: str, updates: dict):
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    db.collection("actionable_links").document(link_id).update(updates)

def delete_actionable_link(link_id: str):
    db.collection("actionable_links").document(link_id).delete()