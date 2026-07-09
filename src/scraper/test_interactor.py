"""Unit tests for CommentInteractor."""

from unittest.mock import AsyncMock

import pytest

from src.scraper.comment_interactor import CommentInteractor
from src.scraper.models import Comment


class MockPage:
    """Mock Playwright page for testing."""

    def __init__(self):
        self.keyboard = AsyncMock()

    async def locator(self, selector: str):
        return MockLocator()

    async def evaluate(self, script: str):
        return 1000


class MockLocator:
    """Mock Playwright locator."""

    async def all(self):
        return []

    async def count(self):
        return 0


@pytest.fixture
def mock_page():
    return MockPage()


@pytest.fixture
def interactor(mock_page):
    return CommentInteractor(page=mock_page, max_comments=10, delay=0.1)


@pytest.mark.asyncio
async def test_find_all_comment_buttons_empty(interactor):
    """Test finding comment buttons on an empty page."""
    buttons = await interactor.find_all_comment_buttons()
    assert buttons == []


@pytest.mark.asyncio
async def test_find_all_post_elements_empty(interactor):
    """Test finding post elements on an empty page."""
    posts = await interactor.find_all_post_elements()
    assert posts == []


@pytest.mark.asyncio
async def test_find_modal_empty(interactor):
    """Test finding modal when none exists."""
    modal = await interactor.find_modal()
    assert modal is None


@pytest.mark.asyncio
async def test_close_modal(interactor):
    """Test closing modal via Escape key."""
    await interactor.close_modal()
    assert interactor.page.keyboard.press.called


@pytest.mark.asyncio
async def test_extract_comments_for_post_no_button(interactor):
    """Test extraction when no comment button is found."""
    comments = await interactor.extract_comments_for_post(0)
    assert comments == []


class TestCommentCleaning:
    """Tests for comment text cleaning."""

    def test_clean_scrambled_text(self):
        """Test cleaning of Facebook scrambled text."""
        raw = "Hello o d S o p s r t e n l 3 h World"
        cleaned = CommentInteractor._clean(raw)
        assert "o d S" not in cleaned
        assert "Hello" in cleaned
        assert "World" in cleaned

    def test_clean_normal_text(self):
        """Test that normal text is preserved."""
        raw = "Este es un comentario normal"
        cleaned = CommentInteractor._clean(raw)
        assert cleaned == "Este es un comentario normal"


class TestToObjects:
    """Tests for converting raw dicts to Comment objects."""

    def test_single_comment(self):
        raw = [{"text": "Test comment", "author": "User", "likes": 5}]
        comments = CommentInteractor._to_objects(raw)
        assert len(comments) == 1
        assert isinstance(comments[0], Comment)
        assert comments[0].text == "Test comment"

    def test_multiple_comments(self):
        raw = [
            {"text": "Comment 1", "author": "User1", "likes": 1},
            {"text": "Comment 2", "author": "User2", "likes": 2},
        ]
        comments = CommentInteractor._to_objects(raw)
        assert len(comments) == 2
        assert comments[0].id != comments[1].id

    def test_empty_author(self):
        raw = [{"text": "Anonymous", "author": "", "likes": 0}]
        comments = CommentInteractor._to_objects(raw)
        assert comments[0].author == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
