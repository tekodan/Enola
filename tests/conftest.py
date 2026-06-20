"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_post_data():
    """Sample post data for testing."""
    return {
        "id": "post-123",
        "text": "Este es un post de prueba con contenido interesante.",
        "author": "Pagina de Prueba",
        "date": "2024-01-15T10:30:00",
        "likes": 150,
        "comments_count": 25,
        "shares": 10,
        "url": "https://facebook.com/post/123",
        "page_id": "page-456",
        "source": "facebook_page",
    }


@pytest.fixture
def sample_comment_data():
    """Sample comment data for testing."""
    return {
        "id": "comment-789",
        "text": "Este es un comentario de prueba.",
        "author": "Usuario de Prueba",
        "date": "2024-01-15T11:00:00",
        "likes": 10,
        "post_id": "post-123",
        "parent_id": None,
        "url": "https://facebook.com/comment/789",
    }


@pytest.fixture
def sample_page_data():
    """Sample page data for testing."""
    return {
        "id": "page-456",
        "name": "Pagina de Prueba",
        "url": "https://facebook.com/page-prueba",
        "likes": 5000,
        "description": "Una pagina de prueba",
        "category": "Entretenimiento",
        "is_public": True,
    }


@pytest.fixture
def violent_texts():
    """Texts that contain violence indicators."""
    return [
        "Te voy a matar si seguís así",
        "Las mujeres solo sirven para cocinar",
        "Si no accedés es tu culpa",
        "No te doy plata para que aprendas",
        "Sos una zorra",
        "Le pegó a su esposa",
    ]


@pytest.fixture
def neutral_texts():
    """Texts that should not contain violence."""
    return [
        "Qué lindo día hace hoy",
        "Feliz cumpleaños",
        "El clima está nice",
        "Compartí esta foto",
        "Hoy comí pizza",
    ]


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.generate = AsyncMock(
        return_value='{"tiene_violencia": false, "tipo": "ninguna", "severidad": "ninguna", "justificacion": "Test", "evidencia": ""}'
    )
    return client


@pytest.fixture
def mock_embeddings_provider():
    """Mock embeddings provider for testing."""
    from unittest.mock import MagicMock

    def embed(texts):
        # Different values per dimension for realistic similarity
        return [[((abs(hash(f"{t}_{i}"))) % 100) / 100 for i in range(5)] for t in texts]

    provider = MagicMock()
    provider.embed.side_effect = embed
    return provider


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary database path for testing."""
    return tmp_path / "test.db"


@pytest.fixture
def temp_chroma_path(tmp_path):
    """Temporary ChromaDB path for testing."""
    return tmp_path / "chroma_db"


# Configure pytest
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
