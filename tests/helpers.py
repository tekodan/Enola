"""Test helpers and utilities."""

import json
from typing import Any


def create_sample_posts(count: int = 10) -> list[dict[str, Any]]:
    """Create sample posts for testing.

    Args:
        count: Number of posts to create

    Returns:
        List of post dictionaries
    """
    posts = []
    for i in range(count):
        posts.append(
            {
                "id": f"post-{i}",
                "text": f"Contenido del post {i}",
                "author": f"Autor {i}",
                "date": "2024-01-15T10:30:00",
                "likes": 100 + i * 10,
                "comments_count": 20 + i * 5,
                "shares": 5 + i,
                "url": f"https://facebook.com/post/{i}",
                "page_id": "page-test",
                "source": "facebook_page",
            }
        )
    return posts


def create_sample_comments(count: int = 20, post_id: str = "post-0") -> list[dict[str, Any]]:
    """Create sample comments for testing.

    Args:
        count: Number of comments to create
        post_id: Parent post ID

    Returns:
        List of comment dictionaries
    """
    comments = []
    for i in range(count):
        comments.append(
            {
                "id": f"comment-{i}",
                "text": f"Comentario {i}",
                "author": f"Usuario {i}",
                "date": "2024-01-15T11:00:00",
                "likes": i * 2,
                "post_id": post_id,
                "parent_id": None,
                "url": f"https://facebook.com/comment/{i}",
            }
        )
    return comments


def create_sample_seed_pages(count: int = 5) -> list[dict[str, Any]]:
    """Create sample seed pages for testing.

    Args:
        count: Number of pages to create

    Returns:
        List of seed page dictionaries
    """
    pages = []
    for i in range(count):
        pages.append(
            {
                "url": f"https://facebook.com/page-{i}",
                "name": f"Pagina {i}",
                "page_id": f"page-id-{i}",
                "is_seed": "true" if i < 3 else "false",
                "discovered_from": None,
                "violence_score": str(0.5 + i * 0.1),
                "posts_count": 50 + i * 10,
            }
        )
    return pages


def create_classification_result(
    tiene_violencia: bool = False, tipo: str = "ninguna", severidad: str = "ninguna"
) -> dict[str, Any]:
    """Create a sample classification result.

    Args:
        tiene_violencia: Whether content has violence
        tipo: Type of violence
        severidad: Severity level

    Returns:
        Classification result dictionary
    """
    return {
        "tiene_violencia": tiene_violencia,
        "tipo": tipo,
        "severidad": severidad,
        "justificacion": f"Test justification for {tipo}",
        "evidencia": "Test evidence",
        "confidence": 0.9 if tiene_violencia else 0.5,
    }


def compare_results(result1: dict, result2: dict) -> bool:
    """Compare two classification results.

    Args:
        result1: First result
        result2: Second result

    Returns:
        True if results are equal
    """
    return (
        result1.get("tiene_violencia") == result2.get("tiene_violencia")
        and result1.get("tipo") == result2.get("tipo")
        and result1.get("severidad") == result2.get("severidad")
    )


def load_json_fixture(fixture_path: str) -> Any:
    """Load a JSON fixture file.

    Args:
        fixture_path: Path to fixture file

    Returns:
        Parsed JSON data
    """
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)
