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
        # User started a new session, check older sessions for context
        older_sessions = get_user_chat_sessions(user_id)
        if older_sessions:
            last_session = older_sessions[0]
            # Use last 2 messages for slight carry-over context if starting fresh
            history.extend(last_session.get("messages", [])[-2:])

        title = payload.question[:50] + "..." if len(payload.question) > 50 else payload.question
        session = create_chat_session(user_id, title)
        session_id = session["id"]
    else:
        session = get_chat_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # INCREASED context window to 10 for better intelligence
        history.extend(session.get("messages", [])[-10:])

    add_message_to_session(session_id, "user", payload.question)

    async def event_generator():
        full_answer = ""
        async for token_json in answer_user_question_stream(payload.question, history=history):
            yield token_json
            try:
                data = json.loads(token_json)
                if data.get("type") == "token":
                    full_answer += data.get("content", "")
            except:
                pass
        
        add_message_to_session(session_id, "ai", full_answer)
        
        from app.services.analytics_services import log_query, log_unanswered_question
        if "I do not have that specific information" in full_answer:
            log_query(answered=False)
            import asyncio
            asyncio.create_task(log_unanswered_question(payload.question))
        else:
            log_query(answered=True)
        
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
    session_id = payload.session_id
    history = []
    if session_id:
        session = get_chat_session(session_id)
        if session:
            history.extend(session.get("messages", [])[-6:])
    else:
        session = create_chat_session("guest", payload.question[:30])
        session_id = session["id"]

    add_message_to_session(session_id, "user", payload.question)

    async def guest_event_generator():
        full_answer = ""
        async for token_json in answer_user_question_stream(payload.question, history=history):
            yield token_json
            try:
                data = json.loads(token_json)
                if data.get("type") == "token":
                    full_answer += data.get("content", "")
            except: pass
        
        add_message_to_session(session_id, "ai", full_answer)
        from app.services.analytics_services import log_query, log_unanswered_question
        if "I do not have that specific information" in full_answer:
            log_query(answered=False)
            import asyncio
            asyncio.create_task(log_unanswered_question(payload.question))
        else:
            log_query(answered=True)
            
        yield json.dumps({"type": "session_info", "session_id": session_id}) + "\n"

    try:
        return StreamingResponse(guest_event_generator(), media_type="application/x-ndjson")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream guest response: {str(e)}")

    try:
        return StreamingResponse(
            guest_event_generator(),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream guest response: {str(e)}")