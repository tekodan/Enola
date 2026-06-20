"""Integration tests for scraper module."""

import json

import pytest

from src.scraper.models import Comment, Post, ScrapeResult


# Fixtures for testing
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
        "reactions": {"like": 100, "love": 50},
        "media_urls": ["https://example.com/image1.jpg"],
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
def posts_fixture(sample_post_data):
    """Create a list of sample posts."""
    posts = []
    for i in range(10):
        post_data = sample_post_data.copy()
        post_data["id"] = f"post-{i}"
        post_data["text"] = f"Contenido del post {i}"
        posts.append(Post(**post_data))
    return posts


@pytest.fixture
def comments_fixture(sample_comment_data):
    """Create a list of sample comments."""
    comments = []
    for i in range(20):
        comment_data = sample_comment_data.copy()
        comment_data["id"] = f"comment-{i}"
        comment_data["text"] = f"Comentario {i}"
        comment_data["post_id"] = "post-123"
        comments.append(Comment(**comment_data))
    return comments


class TestPostIntegration:
    """Integration tests for Post model with fixtures."""

    def test_create_from_fixture(self, sample_post_data):
        """Test creating post from fixture data."""
        post = Post(**sample_post_data)

        assert post.id == "post-123"
        assert post.text == "Este es un post de prueba con contenido interesante."
        assert post.author == "Pagina de Prueba"
        assert post.likes == 150

    def test_post_serialization_roundtrip(self, sample_post_data):
        """Test post serialization and deserialization."""
        post = Post(**sample_post_data)
        data = post.to_dict()
        post_restored = Post(**data)

        assert post.id == post_restored.id
        assert post.text == post_restored.text
        assert post.author == post_restored.author

    def test_batch_posts_creation(self, posts_fixture):
        """Test creating multiple posts from fixtures."""
        assert len(posts_fixture) == 10

        total_likes = sum(p.likes for p in posts_fixture)
        assert total_likes == 1500

    def test_filter_posts_with_content(self, posts_fixture):
        """Test filtering posts that have text content."""
        # Add some empty posts
        posts_fixture.append(Post(id="empty-1", text=""))
        posts_fixture.append(Post(id="empty-2", text="   "))

        posts_with_content = [p for p in posts_fixture if p.has_text()]
        assert len(posts_with_content) == 10


class TestCommentIntegration:
    """Integration tests for Comment model with fixtures."""

    def test_create_from_fixture(self, sample_comment_data):
        """Test creating comment from fixture data."""
        comment = Comment(**sample_comment_data)

        assert comment.id == "comment-789"
        assert comment.text == "Este es un comentario de prueba."
        assert comment.post_id == "post-123"

    def test_comment_serialization_roundtrip(self, sample_comment_data):
        """Test comment serialization and deserialization."""
        comment = Comment(**sample_comment_data)
        data = comment.to_dict()
        comment_restored = Comment(**data)

        assert comment.id == comment_restored.id
        assert comment.text == comment_restored.text

    def test_batch_comments_creation(self, comments_fixture):
        """Test creating multiple comments from fixtures."""
        assert len(comments_fixture) == 20

        # Check all comments belong to same post
        post_ids = set(c.post_id for c in comments_fixture)
        assert len(post_ids) == 1
        assert "post-123" in post_ids

    def test_filter_replies(self, comments_fixture):
        """Test filtering reply comments."""
        # Add some replies
        comments_fixture.append(Comment(id="reply-1", post_id="post-123", parent_id="comment-0"))
        comments_fixture.append(Comment(id="reply-2", post_id="post-123", parent_id="comment-1"))

        replies = [c for c in comments_fixture if c.is_reply()]
        assert len(replies) == 2


class TestScrapeResultIntegration:
    """Integration tests for ScrapeResult."""

    def test_aggregate_results(self, posts_fixture, comments_fixture):
        """Test aggregating multiple posts and comments."""
        result = ScrapeResult(success=True)

        # Add posts in batches
        result.posts.extend(posts_fixture[:5])
        result.posts_found += 5

        result.posts.extend(posts_fixture[5:])
        result.posts_found += 5

        # Add comments
        result.comments.extend(comments_fixture)
        result.comments_found += len(comments_fixture)

        assert len(result.posts) == 10
        assert len(result.comments) == 20
        assert result.posts_found == 10
        assert result.comments_found == 20

    def test_error_handling(self):
        """Test error handling in scrape results."""
        result = ScrapeResult(success=True)

        # Simulate multiple errors
        errors = [
            "Connection timeout to facebook.com",
            "Rate limit exceeded",
            "Parse error: unexpected token",
        ]

        for error in errors:
            result.add_error(error)

        assert result.has_errors is True
        assert len(result.errors) == 3

    def test_merge_multiple_results(self):
        """Test merging multiple scrape results."""
        results = []

        for i in range(3):
            result = ScrapeResult(
                success=True,
                posts=[Post(id=f"post-{i}-{j}") for j in range(5)],
                comments=[Comment(id=f"comment-{i}-{j}") for j in range(10)],
                pages_scraped=1,
                posts_found=5,
                comments_found=10,
            )
            results.append(result)

        # Merge all results
        final_result = results[0]
        for result in results[1:]:
            final_result.merge(result)

        assert len(final_result.posts) == 15
        assert len(final_result.comments) == 30
        assert final_result.pages_scraped == 3


class TestDataPersistence:
    """Tests for data persistence scenarios."""

    def test_save_and_load_posts(self, posts_fixture, tmp_path):
        """Test saving and loading posts to JSON file."""
        posts_file = tmp_path / "posts.json"

        # Save posts
        data = {"posts": [p.to_dict() for p in posts_fixture]}
        posts_file.write_text(json.dumps(data, indent=2))

        # Load posts
        loaded_data = json.loads(posts_file.read_text())
        loaded_posts = [Post(**p) for p in loaded_data["posts"]]

        assert len(loaded_posts) == len(posts_fixture)

        # Verify each post
        for original, loaded in zip(posts_fixture, loaded_posts):
            assert original.id == loaded.id
            assert original.text == loaded.text
            assert original.author == loaded.author

    def test_save_and_load_comments(self, comments_fixture, tmp_path):
        """Test saving and loading comments to JSON file."""
        comments_file = tmp_path / "comments.json"

        # Save comments
        data = {"comments": [c.to_dict() for c in comments_fixture]}
        comments_file.write_text(json.dumps(data, indent=2))

        # Load comments
        loaded_data = json.loads(comments_file.read_text())
        loaded_comments = [Comment(**c) for c in loaded_data["comments"]]

        assert len(loaded_comments) == len(comments_fixture)

        # Verify structure
        for loaded in loaded_comments:
            assert loaded.post_id == "post-123"


class TestFacebookURLParsing:
    """Tests for Facebook URL parsing and validation."""

    def test_parse_page_url(self):
        """Test parsing Facebook page URLs."""
        urls = [
            "https://www.facebook.com/page-name",
            "https://facebook.com/page-name",
            "https://fb.com/page-name",
        ]

        for url in urls:
            post = Post(id="test", url=url)
            assert post.url == url

    def test_parse_post_url(self):
        """Test parsing Facebook post URLs."""
        url = "https://www.facebook.com/page-name/posts/123456789"
        post = Post(id="test", url=url)

        assert "posts" in post.url
        assert "123456789" in post.url

    def test_parse_comment_url(self):
        """Test parsing Facebook comment URLs."""
        url = "https://www.facebook.com/page-name/posts/123456789?comment_id=789"
        comment = Comment(id="test", url=url)

        assert comment.url == url


class TestDataTransformation:
    """Tests for data transformation scenarios."""

    def test_posts_to_analysis_format(self, posts_fixture):
        """Test transforming posts to analysis format."""
        analysis_data = []

        for post in posts_fixture:
            analysis_data.append(
                {
                    "content_type": "post",
                    "content_id": post.id,
                    "text": post.text,
                    "author": post.author,
                    "engagement": post.get_engagement(),
                    "has_media": len(post.media_urls) > 0,
                }
            )

        assert len(analysis_data) == 10
        assert all("content_type" in d for d in analysis_data)
        assert all("engagement" in d for d in analysis_data)

    def test_comments_hierarchy(self, comments_fixture):
        """Test building comment hierarchy."""
        # Add some replies
        comments_fixture.append(
            Comment(
                id="reply-1", text="Reply to comment 0", post_id="post-123", parent_id="comment-0"
            )
        )
        comments_fixture.append(
            Comment(
                id="reply-2", text="Reply to comment 0", post_id="post-123", parent_id="comment-0"
            )
        )

        # Build hierarchy
        root_comments = []
        replies = []

        for comment in comments_fixture:
            if comment.is_reply():
                replies.append(comment)
            else:
                root_comments.append(comment)

        assert len(root_comments) == 20  # 20 original root comments
        assert len(replies) == 2

        # Group replies by parent
        replies_by_parent = {}
        for reply in replies:
            if reply.parent_id not in replies_by_parent:
                replies_by_parent[reply.parent_id] = []
            replies_by_parent[reply.parent_id].append(reply)

        assert "comment-0" in replies_by_parent
        assert len(replies_by_parent["comment-0"]) == 2
