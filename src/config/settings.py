"""Settings module - Pydantic models for configuration."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class AppConfig(BaseModel):
    """Application configuration."""

    name: str = "TFM - Detección de Violencia de Género"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    # URL exposed to the public Streamlit app when redirecting reviewers
    # to the migrated NiceGUI dashboard. Honor env vars first.
    nicegui_url: str = "http://127.0.0.1:8080"


class OllamaConfig(BaseModel):
    """Ollama configuration for LLM and embeddings."""

    base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3.5:9b"
    embedding_model: str = "nomic-embed-text"
    timeout: int = Field(default=120, ge=1)


class ScraperConfig(BaseModel):
    """Scraper configuration."""

    max_posts_per_page: int = Field(default=50, ge=1)
    max_comments_per_post: int = Field(default=100, ge=1)
    delay_between_requests: float = Field(default=2.0, ge=0.0)
    timeout: int = Field(default=60, ge=1)
    user_agent: str = "Mozilla/5.0 (compatible; ResearchBot/1.0)"
    headless: bool = True
    use_interactive: bool = True


class AnalyzerConfig(BaseModel):
    """Analyzer configuration for RAG classification."""

    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    context_chunks: int = Field(default=5, ge=1, le=20)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    # Non-thinking model (gemma4:26b-a4b-it-qat-asst-nothink-64k): no
    # tokens wasted on internal reasoning, so 4096 is comfortable for
    # the multi-label JSON (5 labels × ~150 tokens each).
    max_tokens: int = Field(default=4096, ge=100, le=8192)
    few_shot_examples: int = Field(default=5, ge=1, le=20)


class KnowledgeBaseConfig(BaseModel):
    """Knowledge base configuration for ChromaDB."""

    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    collection_name: str = "violencia_genero"
    persist_directory: str = "data/chroma_db"
    feedback_collection_name: str = "feedback_corrections"


class StorageConfig(BaseModel):
    """Storage configuration for SQLite and exports."""

    database_path: str = "data/tfm.db"
    export_dir: str = "data/exports"
    backup_enabled: bool = True
    backup_interval_hours: int = 24


class DiscoveryConfig(BaseModel):
    """Discovery configuration for automatic page discovery."""

    max_iterations: int = Field(default=3, ge=1, le=10)
    min_violence_score: float = Field(default=0.7, ge=0.0, le=1.0)
    batch_size: int = Field(default=10, ge=1, le=100)
    related_pages_limit: int = Field(default=20, ge=1, le=100)
    groups_keywords: list[str] = Field(
        default_factory=lambda: ["política", "fútbol", "noticias", "debate", "opinión"]
    )


class PipelineConfig(BaseModel):
    """Pipeline orchestration configuration."""

    enable_discovery: bool = True
    enable_backup: bool = True
    checkpoint_interval: int = Field(default=10, ge=1, le=100)
    max_parallel_pages: int = Field(default=3, ge=1, le=10)


class Settings(BaseModel):
    """Main settings class combining all configurations."""

    app: AppConfig = Field(default_factory=AppConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    analyzer: AnalyzerConfig = Field(default_factory=AnalyzerConfig)
    knowledge_base: KnowledgeBaseConfig = Field(default_factory=KnowledgeBaseConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)

    @classmethod
    def from_yaml(cls, path: str) -> "Settings":
        """Load settings from a YAML file."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @field_validator("ollama", mode="before")
    @classmethod
    def validate_ollama_url(cls, v):
        """Ensure Ollama URL has proper format."""
        if isinstance(v, dict) and "base_url" in v:
            url = v["base_url"]
            if not url.startswith(("http://", "https://")):
                v["base_url"] = f"http://{url}"
        return v

    def get_database_url(self) -> str:
        """Get the database URL for SQLAlchemy."""
        return f"sqlite:///{self.storage.database_path}"

    def get_chroma_dir(self) -> Path:
        """Get the ChromaDB persist directory."""
        return Path(self.knowledge_base.persist_directory)

    def get_export_dir(self) -> Path:
        """Get the export directory."""
        return Path(self.storage.export_dir)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    import os

    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if config_path.exists():
        settings = Settings.from_yaml(str(config_path))
    else:
        settings = Settings()
    # Env vars override the YAML defaults for the dual-app deployment.
    host = os.environ.get("ENOLA_HOST")
    port = os.environ.get("ENOLA_PORT")
    if host or port:
        port_str = port or "8080"
        settings.app.nicegui_url = f"http://{host or '127.0.0.1'}:{port_str}"
    return settings
