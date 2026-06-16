from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Sydney"
    app_version: str = "0.1.0"
    debug: bool = True

    database_url: str = "sqlite:///./data/sydney.db"

    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"

    embedding_model: str = "BAAI/bge-small-en-v1.5"

    clinvar_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    pubmed_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    max_pubmed_results: int = 20
    cache_ttl_hours: int = 24

    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
