from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.core.dependencies import get_current_user
from app.schemas.chat import AskRequest
from app.services.rag import answer_user_question_stream
from app.services.firestore_services import (
    create_chat_session, 
    get_user_chat_sessions, 
    get_chat_session, 
    add_message_to_session
)
import json
from datetime import datetime
from fastapi import Request
from app.core.rate_limit import limiter

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/sessions")
async def get_sessions(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("email")
    return get_user_chat_sessions(user_id)

@router.get("/sessions/{session_id}")
async def get_session_details(session_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("email")
    session = get_chat_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/ask")
@limiter.limit("10/minute")
async def ask_question(
    request: Request,
    payload: AskRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("email")
    session_id = payload.session_id
    history = []

    if not session_id:
        # User started a new session, but requested we look at older sessions for context
        older_sessions = get_user_chat_sessions(user_id)
        if older_sessions:
            last_session = older_sessions[0]
            # Use the last 4 messages from the most recent previous session
            history.extend(last_session.get("messages", [])[-4:])

        # Create new session if none provided
        title = payload.question[:50] + "..." if len(payload.question) > 50 else payload.question
        session = create_chat_session(user_id, title)
        session_id = session["id"]
    else:
        # Continuing existing session, grab history
        session = get_chat_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        history.extend(session.get("messages", [])[-6:]) # Last 6 messages

    # Save user message
    add_message_to_session(session_id, "user", payload.question)

    async def event_generator():
        full_answer = ""
        # The generator from rag.py yields stringified JSON tokens
        async for token_json in answer_user_question_stream(payload.question, history=history):
            yield token_json
            try:
                data = json.loads(token_json)
                if data.get("type") == "token":
                    full_answer += data.get("content", "")
            except:
                pass
        
        # Save AI message after stream ends
        add_message_to_session(session_id, "ai", full_answer)
        
        # Log analytics
        from app.services.analytics_services import log_query, log_unanswered_question
        if "I do not have that specific information" in full_answer:
            log_query(answered=False)
            # Create task to log the unanswered question detail
            import asyncio
            asyncio.create_task(log_unanswered_question(payload.question))
        else:
            log_query(answered=True)
        
        # Final token with session_id for the frontend to know
        yield json.dumps({"type": "session_info", "session_id": session_id}) + "\n"

    try:
        return StreamingResponse(
            event_generator(),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream: {str(e)}")


@router.post("/guest/ask")
@limiter.limit("10/minute")
async def ask_guest_question(request: Request, payload: AskRequest):
    # For guests, we don't save to session history or use current_user
    async def guest_event_generator():
        full_answer = ""
        async for token_json in answer_user_question_stream(payload.question):
            yield token_json
            try:
                data = json.loads(token_json)
                if data.get("type") == "token":
                    full_answer += data.get("content", "")
            except:
                pass
        
        # Log analytics for guest too
        from app.services.analytics_services import log_query, log_unanswered_question
        if "I do not have that specific information" in full_answer:
            log_query(answered=False)
            import asyncio
            asyncio.create_task(log_unanswered_question(payload.question))
        else:
            log_query(answered=True)

    try:
        return StreamingResponse(
            guest_event_generator(),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream guest response: {str(e)}")