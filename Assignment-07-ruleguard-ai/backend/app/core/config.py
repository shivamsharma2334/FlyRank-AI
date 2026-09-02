from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "models/embedding-001"

    llm_enabled: bool = True
    llm_stub: bool = False

    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    rag_top_k: int = 4

    prompt_version: str = "risk-v1"
    review_threshold: float = 0.75

    cors_origins: str = "http://localhost:5173"

    kb_dir: Path = BASE_DIR / "kb"
    faiss_index_dir: Path = BASE_DIR / "data" / "faiss_index"
    prompts_dir: Path = BASE_DIR / "app" / "prompts"
    logs_dir: Path = BASE_DIR / "logs"


settings = Settings()
settings.logs_dir.mkdir(parents=True, exist_ok=True)
