"""Tests for Facebook URL classification utilities."""

import pytest

from src.scraper.models import ContentSource
from src.scraper.url_utils import (
    classify_facebook_url,
    is_facebook_group_url,
    is_facebook_page_url,
    is_facebook_post_url,
    is_facebook_reel_url,
)


class TestClassifyFacebookUrl:
    """Tests for classify_facebook_url."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.facebook.com/Mentalidad100", ContentSource.FACEBOOK_PAGE),
            ("https://facebook.com/some.page", ContentSource.FACEBOOK_PAGE),
            (
                "https://www.facebook.com/100080046996960/posts/999061662772058/",
                ContentSource.FACEBOOK_POST,
            ),
            (
                "https://www.facebook.com/1146333735/posts/10242133633014430/",
                ContentSource.FACEBOOK_POST,
            ),
            (
                "https://www.facebook.com/story.php?story_fbid=122315053604209724&id=61556291746165",
                ContentSource.FACEBOOK_POST,
            ),
            ("https://www.facebook.com/reel/993030670163319", ContentSource.FACEBOOK_POST),
            ("https://www.facebook.com/reel/2053208055579787", ContentSource.FACEBOOK_POST),
            ("https://www.facebook.com/groups/groupname", ContentSource.FACEBOOK_GROUP),
            ("https://www.facebook.com/groups/groupname/posts/123", ContentSource.FACEBOOK_GROUP),
            ("https://www.facebook.com/share/abc123", ContentSource.FACEBOOK_POST),
            ("", ContentSource.UNKNOWN),
            ("https://www.facebook.com/", ContentSource.UNKNOWN),
        ],
    )
    def test_classification(self, url: str, expected: ContentSource):
        """Test URL classification for various Facebook URL patterns."""
        assert classify_facebook_url(url) == expected


class TestHelperFunctions:
    """Tests for boolean helper functions."""

    def test_is_facebook_page_url(self):
        assert is_facebook_page_url("https://www.facebook.com/Mentalidad100") is True
        assert is_facebook_page_url("https://www.facebook.com/reel/123") is False

    def test_is_facebook_post_url(self):
        assert is_facebook_post_url("https://www.facebook.com/page/posts/123") is True
        assert is_facebook_post_url("https://www.facebook.com/page") is False

    def test_is_facebook_reel_url(self):
        assert is_facebook_reel_url("https://www.facebook.com/reel/993030670163319") is True
        assert is_facebook_reel_url("https://www.facebook.com/page/posts/123") is False

    def test_is_facebook_group_url(self):
        assert is_facebook_group_url("https://www.facebook.com/groups/groupname") is True
        assert is_facebook_group_url("https://www.facebook.com/page") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
