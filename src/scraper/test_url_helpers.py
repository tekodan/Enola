"""Tests for URL helpers and post ID extraction."""

import pytest

from src.scraper.facebook import FacebookScraper


class TestExtractPostIdFromUrl:
    """Tests for ``_extract_post_id_from_url``."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            (
                "https://www.facebook.com/100080046996960/posts/999061662772058/",
                "999061662772058",
            ),
            (
                "https://www.facebook.com/1146333735/posts/10242133633014430/",
                "10242133633014430",
            ),
            (
                "https://www.facebook.com/story.php?story_fbid=122315053604209724&id=61556291746165",
                "122315053604209724",
            ),
            (
                "https://www.facebook.com/reel/993030670163319",
                "993030670163319",
            ),
            (
                "https://www.facebook.com/reel/2053208055579787",
                "2053208055579787",
            ),
            ("https://www.facebook.com/Mentalidad100", None),
            ("", None),
        ],
    )
    def test_extracts_post_id(self, url: str, expected: str | None):
        """Test post ID extraction from various Facebook URL patterns."""
        result = FacebookScraper._extract_post_id_from_url(url)
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
