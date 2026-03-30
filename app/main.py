from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.chat import router as chat_router

from app.core.rate_limit import limiter

from app.middleware.security_headers import SecurityHeadersMiddleware

app = FastAPI(
    title="Bowen AI API",
    description="RAG_based AI system for bowen University users",
    version="1.0.0"
)

# Wire up the rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, this can be restricted to specific domains if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)

@app.get("/api")
async def root():
    return{
        "message": "Bowen AI API is running"
    }

@app.get("/health")
async def health_check():
    return{
        "status": "health",
        "service": "Bowen AI Backend"
    }

# Mount the frontend directory natively (do this AFTER API routes!)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")