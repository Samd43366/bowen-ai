from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str ="Bowen AI"
    FIREBASE_CREDENTIALS: str | None = None
    FIREBASE_PROJECT_ID: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 60

    QDRANT_URL: str
    QDRANT_API_KEY: str 
    QDRANT_COLLECTION_NAME: str = "bowen_documents"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    UPLOAD_DIR: str = "uploads"

    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_MODEL: str = "llama-3.1-8b-instant"

    EMAIL_FROM_NAME: str = "Bowen AI"
    EMAIL_FROM: str

    SMTP_SERVER: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    
    BREVO_API_KEY: str | None = None
    
    ADMIN_REGISTRATION_SECRET: str

    model_config = SettingsConfigDict(
    env_file=".env", 
    extra="ignore",
    case_sensitive=True   
    )
settings = Settings()
