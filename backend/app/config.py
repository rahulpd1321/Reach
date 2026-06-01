from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM: gemini (default) or openai
    llm_provider: str = "gemini"
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    # Comma-separated extra models to try after primary (on 429 / quota)
    gemini_model_fallbacks: str = "gemini-1.5-flash,gemini-2.5-flash"
    # If Gemini fails and OPENAI_API_KEY is set, try OpenAI once
    auto_fallback_openai: bool = True

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    use_openai_embeddings: bool = False
    chroma_persist_dir: str = "./data/chroma"
    frontend_origin: str = "http://localhost:3000"
    # Extra origins, comma-separated (e.g. https://your-app.vercel.app)
    frontend_origins: str = ""
    # Regex for preview deploys (Vercel)
    cors_origin_regex: str = r"https://.*\.vercel\.app"
    chunk_size: int = 500
    chunk_overlap: int = 80
    retrieval_k: int = 6
    # e.g. chrome, firefox — helps Instagram when login is required
    ytdlp_cookies_browser: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
