"""Unit tests for configuration module."""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config.settings import (
    AnalyzerConfig,
    AppConfig,
    DiscoveryConfig,
    KnowledgeBaseConfig,
    OllamaConfig,
    PipelineConfig,
    ScraperConfig,
    Settings,
    StorageConfig,
    get_settings,
)


class TestAppConfig:
    """Tests for AppConfig."""

    def test_defaults(self):
        """Test default values."""
        config = AppConfig()
        assert config.name == "TFM - Detección de Violencia de Género"
        assert config.version == "1.0.0"
        assert config.debug is False
        assert config.log_level == "INFO"

    def test_custom_values(self):
        """Test custom values."""
        config = AppConfig(name="Test App", version="2.0.0", debug=True, log_level="DEBUG")
        assert config.name == "Test App"
        assert config.version == "2.0.0"
        assert config.debug is True
        assert config.log_level == "DEBUG"

    def test_nicegui_url_default(self):
        """The NiceGUI URL defaults to localhost:8080."""
        config = AppConfig()
        assert config.nicegui_url == "http://127.0.0.1:8080"

    def test_nicegui_url_custom(self):
        config = AppConfig(nicegui_url="http://0.0.0.0:9090")
        assert config.nicegui_url == "http://0.0.0.0:9090"


class TestOllamaConfig:
    """Tests for OllamaConfig."""

    def test_defaults(self):
        """Test default values."""
        config = OllamaConfig()
        assert config.base_url == "http://localhost:11434"
        assert config.llm_model == "qwen3.5:9b"
        assert config.embedding_model == "nomic-embed-text"
        assert config.timeout == 120

    def test_custom_url(self):
        """Test custom URL."""
        config = OllamaConfig(base_url="http://custom:11434")
        assert config.base_url == "http://custom:11434"

    def test_timeout_validation(self):
        """Test timeout must be positive."""
        with pytest.raises(ValidationError):
            OllamaConfig(timeout=0)
        with pytest.raises(ValidationError):
            OllamaConfig(timeout=-1)


class TestScraperConfig:
    """Tests for ScraperConfig."""

    def test_defaults(self):
        """Test default values."""
        config = ScraperConfig()
        assert config.max_posts_per_page == 50
        assert config.max_comments_per_post == 100
        assert config.delay_between_requests == 2.0
        assert config.timeout == 60

    def test_max_posts_validation(self):
        """Test max_posts must be positive."""
        with pytest.raises(ValidationError):
            ScraperConfig(max_posts_per_page=0)
        with pytest.raises(ValidationError):
            ScraperConfig(max_posts_per_page=-1)


class TestAnalyzerConfig:
    """Tests for AnalyzerConfig."""

    def test_defaults(self):
        """Test default values."""
        config = AnalyzerConfig()
        assert config.similarity_threshold == 0.7
        assert config.context_chunks == 5
        assert config.temperature == 0
        assert config.max_tokens == 4096
        assert config.few_shot_examples == 5

    def test_threshold_validation(self):
        """Test threshold must be between 0 and 1."""
        config = AnalyzerConfig(similarity_threshold=0.5)
        assert config.similarity_threshold == 0.5

        with pytest.raises(ValidationError):
            AnalyzerConfig(similarity_threshold=-0.1)

        with pytest.raises(ValidationError):
            AnalyzerConfig(similarity_threshold=1.5)


class TestKnowledgeBaseConfig:
    """Tests for KnowledgeBaseConfig."""

    def test_defaults(self):
        """Test default values."""
        config = KnowledgeBaseConfig()
        assert config.chunk_size == 500
        assert config.chunk_overlap == 50
        assert config.collection_name == "violencia_genero"
        assert config.persist_directory == "data/chroma_db"

    def test_chunk_size_validation(self):
        """Test chunk_size must be positive."""
        with pytest.raises(ValidationError):
            KnowledgeBaseConfig(chunk_size=0)


class TestStorageConfig:
    """Tests for StorageConfig."""

    def test_defaults(self):
        """Test default values."""
        config = StorageConfig()
        assert config.database_path == "data/tfm.db"
        assert config.export_dir == "data/exports"
        assert config.backup_enabled is True
        assert config.backup_interval_hours == 24


class TestDiscoveryConfig:
    """Tests for DiscoveryConfig."""

    def test_defaults(self):
        """Test default values."""
        config = DiscoveryConfig()
        assert config.max_iterations == 3
        assert config.min_violence_score == 0.7
        assert config.batch_size == 10
        assert config.related_pages_limit == 20
        assert "política" in config.groups_keywords

    def test_max_iterations_validation(self):
        """Test max_iterations must be between 1 and 10."""
        config = DiscoveryConfig(max_iterations=5)
        assert config.max_iterations == 5

        with pytest.raises(ValidationError):
            DiscoveryConfig(max_iterations=0)

        with pytest.raises(ValidationError):
            DiscoveryConfig(max_iterations=15)


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_defaults(self):
        """Test default values."""
        config = PipelineConfig()
        assert config.enable_discovery is True
        assert config.enable_backup is True
        assert config.checkpoint_interval == 10
        assert config.max_parallel_pages == 3


class TestSettings:
    """Tests for Settings main class."""

    def test_defaults(self):
        """Test default values for all configs."""
        settings = Settings()

        assert isinstance(settings.app, AppConfig)
        assert isinstance(settings.ollama, OllamaConfig)
        assert isinstance(settings.scraper, ScraperConfig)
        assert isinstance(settings.analyzer, AnalyzerConfig)
        assert isinstance(settings.knowledge_base, KnowledgeBaseConfig)
        assert isinstance(settings.storage, StorageConfig)
        assert isinstance(settings.discovery, DiscoveryConfig)
        assert isinstance(settings.pipeline, PipelineConfig)

    def test_from_yaml(self):
        """Test loading from YAML file."""
        yaml_content = """
app:
  name: "Test App"
  version: "3.0.0"
  debug: true

ollama:
  base_url: "http://test:11434"
  llm_model: "llama3"

scraper:
  max_posts_per_page: 100

analyzer:
  similarity_threshold: 0.8

knowledge_base:
  collection_name: "test_collection"

storage:
  database_path: "test.db"

discovery:
  max_iterations: 5

pipeline:
  enable_discovery: false
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            settings = Settings.from_yaml(temp_path)

            assert settings.app.name == "Test App"
            assert settings.app.version == "3.0.0"
            assert settings.app.debug is True
            assert settings.ollama.base_url == "http://test:11434"
            assert settings.ollama.llm_model == "llama3"
            assert settings.scraper.max_posts_per_page == 100
            assert settings.analyzer.similarity_threshold == 0.8
            assert settings.knowledge_base.collection_name == "test_collection"
            assert settings.storage.database_path == "test.db"
            assert settings.discovery.max_iterations == 5
            assert settings.pipeline.enable_discovery is False
        finally:
            Path(temp_path).unlink()

    def test_get_database_url(self):
        """Test database URL generation."""
        settings = Settings()
        url = settings.get_database_url()
        assert url == "sqlite:///data/tfm.db"

    def test_get_chroma_dir(self):
        """Test ChromaDB directory."""
        settings = Settings()
        chroma_dir = settings.get_chroma_dir()
        assert chroma_dir == Path("data/chroma_db")

    def test_get_export_dir(self):
        """Test export directory."""
        settings = Settings()
        export_dir = settings.get_export_dir()
        assert export_dir == Path("data/exports")

    def test_validate_ollama_url(self):
        """Test URL validation for Ollama."""
        settings = Settings(ollama={"base_url": "localhost:11434"})
        assert settings.ollama.base_url.startswith("http://")


class TestGetSettings:
    """Tests for get_settings function."""

    def test_cached_settings(self):
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_cache_clear(self):
        """Test cache clear functionality."""
        get_settings.cache_clear()

        # After clear, should get new instance
        settings = get_settings()
        assert isinstance(settings, Settings)
