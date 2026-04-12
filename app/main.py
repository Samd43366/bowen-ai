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

from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.scraper_services import run_scraper_sync

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler when app starts
    scheduler.add_job(run_scraper_sync, 'cron', hour=0, minute=30) # Run at 12:30 AM daily
    scheduler.start()
    yield
    # Shutdown when app stops
    scheduler.shutdown()

app = FastAPI(
    title="Bowen AI API",
    description="RAG_based AI system for bowen University users",
    version="1.0.0",
    lifespan=lifespan
)

# Wire up the rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Middlewares
app.add_middleware(SecurityHeadersMiddleware)

# List of allowed origins in production and development
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://localhost:5173",
    "https://huggingface.co",
    "https://*.hf.space", # Hugging Face Spaces
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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