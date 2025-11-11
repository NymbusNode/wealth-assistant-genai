from pydantic import BaseModel
import os
class Settings(BaseModel):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    TOP_K: int = int(os.getenv("TOP_K", "4"))
    CHUNK_TOKENS: int = int(os.getenv("CHUNK_TOKENS", "700"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))
settings = Settings()
