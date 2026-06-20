"""Unit tests for scraper module."""

from datetime import datetime

from src.scraper.models import (
    Comment,
    ContentSource,
    GroupInfo,
    PageInfo,
    Post,
    ScrapeResult,
)


class TestPost:
    """Tests for Post model."""

    def test_create_post_minimal(self):
        """Test creating a post with minimal data."""
        post = Post(id="post-123")
        assert post.id == "post-123"
        assert post.text == ""
        assert post.author == ""
        assert post.likes == 0
        assert post.comments_count == 0
        assert post.shares == 0

    def test_create_post_full(self):
        """Test creating a post with all fields."""
        post = Post(
            id="post-123",
            text="Este es un post de prueba",
            author="Pagina de Prueba",
            date=datetime(2024, 1, 15, 10, 30),
            likes=100,
            comments_count=25,
            shares=10,
            url="https://facebook.com/post/123",
            page_id="page-456",
            source=ContentSource.FACEBOOK_PAGE,
            reactions={"like": 80, "love": 20},
            media_urls=["https://example.com/image.jpg"],
        )

        assert post.id == "post-123"
        assert post.text == "Este es un post de prueba"
        assert post.author == "Pagina de Prueba"
        assert post.likes == 100
        assert post.comments_count == 25
        assert post.shares == 10
        assert post.source == ContentSource.FACEBOOK_PAGE

    def test_validate_counts_string(self):
        """Test validation of string counts."""
        post = Post(id="test", likes="150", comments_count="30")
        assert post.likes == 150
        assert post.comments_count == 30

    def test_validate_counts_negative(self):
        """Test that negative counts are converted to 0."""
        post = Post(id="test", likes=-50)
        assert post.likes == 0

    def test_validate_counts_none(self):
        """Test that None counts are converted to 0."""
        post = Post(id="test", likes=None)
        assert post.likes == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        post = Post(id="post-123", text="Test content", author="Test Author", likes=50)
        data = post.to_dict()

        assert data["id"] == "post-123"
        assert data["text"] == "Test content"
        assert data["author"] == "Test Author"
        assert data["likes"] == 50
        assert "created_at" in data

    def test_has_text(self):
        """Test has_text method."""
        post_empty = Post(id="test")
        assert post_empty.has_text() is False

        post_text = Post(id="test", text="Some content")
        assert post_text.has_text() is True

        post_whitespace = Post(id="test", text="   ")
        assert post_whitespace.has_text() is False

    def test_get_engagement(self):
        """Test engagement calculation."""
        post = Post(id="test", likes=100, comments_count=50, shares=25)
        assert post.get_engagement() == 175


class TestComment:
    """Tests for Comment model."""

    def test_create_comment_minimal(self):
        """Test creating a comment with minimal data."""
        comment = Comment(id="comment-123")
        assert comment.id == "comment-123"
        assert comment.text == ""
        assert comment.author == ""
        assert comment.likes == 0

    def test_create_comment_full(self):
        """Test creating a comment with all fields."""
        comment = Comment(
            id="comment-123",
            text="Este es un comentario de prueba",
            author="Usuario de Prueba",
            date=datetime(2024, 1, 15, 12, 0),
            likes=15,
            post_id="post-456",
            parent_id="comment-789",
            url="https://facebook.com/comment/123",
        )

        assert comment.id == "comment-123"
        assert comment.text == "Este es un comentario de prueba"
        assert comment.post_id == "post-456"
        assert comment.parent_id == "comment-789"

    def test_validate_likes_string(self):
        """Test validation of string likes."""
        comment = Comment(id="test", likes="200")
        assert comment.likes == 200

    def test_is_reply(self):
        """Test is_reply method."""
        comment_no_reply = Comment(id="test", parent_id=None)
        assert comment_no_reply.is_reply() is False

        comment_reply = Comment(id="test", parent_id="parent-123")
        assert comment_reply.is_reply() is True

    def test_has_text(self):
        """Test has_text method."""
        comment_empty = Comment(id="test")
        assert comment_empty.has_text() is False

        comment_text = Comment(id="test", text="Some comment")
        assert comment_text.has_text() is True


class TestPageInfo:
    """Tests for PageInfo model."""

    def test_create_page_info_minimal(self):
        """Test creating page info with minimal data."""
        page = PageInfo(id="page-123")
        assert page.id == "page-123"
        assert page.name == ""
        assert page.likes == 0
        assert page.is_public is True

    def test_create_page_info_full(self):
        """Test creating page info with all fields."""
        page = PageInfo(
            id="page-123",
            name="Pagina de Prueba",
            url="https://facebook.com/page-test",
            likes=10000,
            description="Una pagina de prueba",
            category="Entretenimiento",
            is_public=True,
        )

        assert page.name == "Pagina de Prueba"
        assert page.likes == 10000
        assert page.category == "Entretenimiento"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        page = PageInfo(id="page-123", name="Test Page", likes=500)
        data = page.to_dict()

        assert data["id"] == "page-123"
        assert data["name"] == "Test Page"
        assert data["likes"] == 500
        assert "scraped_at" in data


class TestGroupInfo:
    """Tests for GroupInfo model."""

    def test_create_group_info_minimal(self):
        """Test creating group info with minimal data."""
        group = GroupInfo(id="group-123")
        assert group.id == "group-123"
        assert group.name == ""
        assert group.members == 0

    def test_create_group_info_full(self):
        """Test creating group info with all fields."""
        group = GroupInfo(
            id="group-123",
            name="Grupo de Prueba",
            url="https://facebook.com/groups/test",
            members=5000,
            description="Un grupo de prueba",
            privacy="public",
        )

        assert group.name == "Grupo de Prueba"
        assert group.members == 5000
        assert group.privacy == "public"


class TestScrapeResult:
    """Tests for ScrapeResult model."""

    def test_create_scrape_result_success(self):
        """Test creating a successful scrape result."""
        result = ScrapeResult(success=True)
        assert result.success is True
        assert result.posts == []
        assert result.comments == []
        assert result.errors == []
        assert result.pages_scraped == 0

    def test_create_scrape_result_with_data(self):
        """Test creating result with posts and comments."""
        posts = [Post(id="1"), Post(id="2")]
        comments = [Comment(id="c1")]

        result = ScrapeResult(
            success=True,
            posts=posts,
            comments=comments,
            pages_scraped=1,
            posts_found=2,
            comments_found=1,
        )

        assert len(result.posts) == 2
        assert len(result.comments) == 1
        assert result.pages_scraped == 1

    def test_add_error(self):
        """Test adding error messages."""
        result = ScrapeResult(success=True)
        result.add_error("Connection timeout")
        result.add_error("Parse error")

        assert len(result.errors) == 2
        assert result.has_errors is True

    def test_merge(self):
        """Test merging two scrape results."""
        result1 = ScrapeResult(
            success=True,
            posts=[Post(id="1")],
            comments=[Comment(id="c1")],
            pages_scraped=1,
            posts_found=1,
            comments_found=1,
        )

        result2 = ScrapeResult(
            success=True,
            posts=[Post(id="2"), Post(id="3")],
            comments=[Comment(id="c2")],
            pages_scraped=1,
            posts_found=2,
            comments_found=1,
        )

        result1.merge(result2)

        assert len(result1.posts) == 3
        assert len(result1.comments) == 2
        assert result1.pages_scraped == 2

    def test_total_items(self):
        """Test total items calculation."""
        result = ScrapeResult(
            success=True,
            posts=[Post(id="1"), Post(id="2")],
            comments=[Comment(id="c1")],
            pages=[PageInfo(id="p1")],
        )

        assert result.total_items == 4


class TestContentSource:
    """Tests for ContentSource enum."""

    def test_content_source_values(self):
        """Test ContentSource enum values."""
        assert ContentSource.FACEBOOK_PAGE.value == "facebook_page"
        assert ContentSource.FACEBOOK_GROUP.value == "facebook_group"
        assert ContentSource.FACEBOOK_POST.value == "facebook_post"
        assert ContentSource.UNKNOWN.value == "unknown"

    def test_content_source_from_string(self):
        """Test creating ContentSource from string."""
        source = ContentSource("facebook_page")
        assert source == ContentSource.FACEBOOK_PAGE
