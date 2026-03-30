from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from app.core.dependencies import admin_required, superadmin_required, document_admin_required
from app.services.document_pipeline import process_document, process_document_background
from app.services.pdf_services import extract_text_from_pdf
from app.services.word_services import extract_text_from_docx
from app.services.firestore_services import (
    save_document_metadata, 
    get_all_documents, 
    delete_document_by_filename, 
    get_document_by_id,
    get_all_users,
    approve_admin,
    delete_user,
    log_admin_action,
    get_recent_audit_logs,
    add_category,
    get_all_categories,
    delete_category,
    get_document_count_by_category
)
from app.services.qdrant_services import delete_document_chunks
import re

def secure_filename(filename: str) -> str:
    """
    Sanitize filename: allow only alphanumeric, underscores, hyphens and dots.
    """
    # Remove any path separators
    filename = filename.replace("\\", "/").split("/")[-1]
    # Replace anything not alphanumeric, dot, underscore, or hyphen
    filename = re.sub(r'[^a-zA-Z0-9\._-]', '_', filename)
    return filename

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form("Uncategorized"),
    current_admin: dict = Depends(document_admin_required)
):
    try:
        allowed_extensions = (".pdf", ".docx", ".doc")
        if not file.filename.lower().endswith(allowed_extensions):
            raise HTTPException(status_code=400, detail=f"Only {', '.join(allowed_extensions)} files are allowed.")

        file_bytes = await file.read()
        
        # Extract text early to prevent empty uploads
        ext = file.filename.lower().split('.')[-1]
        if ext == 'pdf':
            full_text = extract_text_from_pdf(file_bytes)
        else:
            full_text = extract_text_from_docx(file_bytes)

        if not full_text or not full_text.strip():
            raise HTTPException(status_code=400, detail="The uploaded document contains no readable text.")

        safe_filename = secure_filename(file.filename)

        doc = save_document_metadata({
            "filename": safe_filename, 
            "status": "processing",
            "chunks_indexed": 0,
            "category": category
        })

        background_tasks.add_task(
            process_document_background,
            doc["id"],
            safe_filename,
            full_text,
            category
        )

        log_admin_action(current_admin["email"], "UPLOAD_DOCUMENT", f"{file.filename} in {category}")

        return {"message": "Document uploaded and is being processed.", "document_id": doc["id"], "filename": file.filename}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload and process document: {str(e)}"
        )


@router.get("/documents")
async def get_documents(current_admin: dict = Depends(document_admin_required)):
    docs = get_all_documents()
    return {"documents": docs}


@router.get("/documents/{document_id}")
async def get_document(document_id: str, current_admin: dict = Depends(document_admin_required)):
    doc = get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/categories")
async def fetch_categories(current_admin: dict = Depends(admin_required)):
    cats = get_all_categories()
    if "Uncategorized" not in cats:
        cats.insert(0, "Uncategorized")
    return {"categories": cats}

from pydantic import BaseModel
class CategoryRequest(BaseModel):
    name: str

@router.post("/categories")
async def create_new_category(request: CategoryRequest, current_admin: dict = Depends(admin_required)):
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    add_category(name)
    log_admin_action(current_admin["email"], "CREATE_CATEGORY", name)
    return {"message": "Category created"}

@router.delete("/categories/{name}")
async def remove_category(name: str, current_admin: dict = Depends(admin_required)):
    if name == "Uncategorized":
        raise HTTPException(status_code=400, detail="Cannot delete default category.")
    count = get_document_count_by_category(name)
    if count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete category '{name}' because it contains {count} documents.")
    delete_category(name)
    log_admin_action(current_admin["email"], "DELETE_CATEGORY", name)
    return {"message": "Category deleted"}


@router.delete("/documents/{filename}")
async def delete_document(filename: str, current_admin: dict = Depends(document_admin_required)):
    try:
        safe_filename = secure_filename(filename)
        delete_document_chunks(safe_filename)
        delete_document_by_filename(safe_filename)
        log_admin_action(current_admin["email"], "DELETE_DOCUMENT", safe_filename)
        return {"message": f"Document '{safe_filename}' deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )

# Superadmin specific routes
@router.get("/users")
async def get_users_list(current_admin: dict = Depends(superadmin_required)):
    users = get_all_users() # Uses scrub=True by default now
    return {"users": users}

@router.put("/users/{email}/verify")
async def verify_admin_route(email: str, current_admin: dict = Depends(superadmin_required)):
    try:
        approve_admin(email)
        log_admin_action(current_admin["email"], "APPROVE_USER", email)
        return {"message": f"User {email} successfully approved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{email}")
async def delete_user_route(email: str, current_admin: dict = Depends(superadmin_required)):
    if email == current_admin.get("email"):
        raise HTTPException(status_code=400, detail="Superadmin cannot delete themselves")
    try:
        delete_user(email)
        log_admin_action(current_admin["email"], "DELETE_USER", email)
        return {"message": f"User {email} eradicated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_admin_stats(current_admin: dict = Depends(superadmin_required)):
    from app.core.database import db
    users = get_all_users()
    docs = get_all_documents()
    sessions_count = len(list(db.collection("chat_sessions").stream()))
    
    return {
        "total_users": len(users),
        "total_pending_admins": len([u for u in users if u.get("role") == "admin" and not u.get("is_approved")]),
        "total_system_admins": len([u for u in users if u.get("role") in ["admin", "superadmin"]]),
        "total_documents": len(docs),
        "total_chat_sessions": sessions_count
    }

@router.get("/analytics")
async def get_analytics_data(current_admin: dict = Depends(superadmin_required)):
    from app.core.database import db
    
    docs = db.collection("analytics").stream()
    data_by_month = {}
    
    for doc in docs:
        date_str = doc.id
        if len(date_str) >= 7:
            month_key = date_str[:7] # "YYYY-MM"
            if month_key not in data_by_month:
                data_by_month[month_key] = {"answered": 0, "unanswered": 0, "users": set()}
            
            d = doc.to_dict()
            data_by_month[month_key]["answered"] += d.get("answered_questions", 0)
            data_by_month[month_key]["unanswered"] += d.get("unanswered_questions", 0)
            
            for email in d.get("active_users", []):
                data_by_month[month_key]["users"].add(email)
                
    results = {}
    # Sort keys reverse chronologically
    sorted_keys = sorted(data_by_month.keys(), reverse=True)
    
    for mk in sorted_keys:
        meta = data_by_month[mk]
        results[mk] = {
            "answered": meta["answered"],
            "unanswered": meta["unanswered"],
            "active_users_count": len(meta["users"])
        }
        
    return {"monthly_data": results}

@router.get("/logs")
async def get_system_logs(current_admin: dict = Depends(superadmin_required)):
    logs = get_recent_audit_logs(limit=30)
    # Format them as strings for simpler frontend display if needed, 
    # but returning raw objects lets frontend be smarter.
    return {"logs": logs}

@router.get("/unanswered")
async def get_unanswered_questions(current_admin: dict = Depends(admin_required)):
    """
    Retrieve questions the AI couldn't answer, grouped by category.
    """
    from app.core.database import db
    
    docs = db.collection("unanswered_questions").order_by("count", direction="DESCENDING").stream()
    questions = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        questions.append(d)
    
    return {"unanswered": questions}

@router.delete("/unanswered/{question_id}")
async def delete_unanswered_question(question_id: str, current_admin: dict = Depends(admin_required)):
    """
    Clear an unanswered question from the list (e.g., after the info has been uploaded).
    """
    from app.core.database import db
    db.collection("unanswered_questions").document(question_id).delete()
    return {"message": "Knowledge gap cleared"}