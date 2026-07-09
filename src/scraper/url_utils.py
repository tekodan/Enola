"""URL utilities for Facebook content classification."""

from urllib.parse import urlparse

from src.scraper.models import ContentSource


def _is_facebook_domain(url: str) -> bool:
    """Return True if the URL belongs to facebook.com."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    # Accept facebook.com and its subdomains (e.g. m.facebook.com, www.facebook.com)
    return netloc == "facebook.com" or netloc.endswith(".facebook.com")


def classify_facebook_url(url: str) -> ContentSource:
    """Classify a Facebook URL as page, post, reel, group, or unknown.

    Detection is based purely on URL patterns, independent of any
    comments/sections in seed files.

    Supported patterns:
      - Page:  facebook.com/page-name (no post/reel/group path)
      - Post:  facebook.com/.../posts/<id>
               facebook.com/story.php?story_fbid=...
               facebook.com/share/<id>/
               facebook.com/photo.php?fbid=...
               facebook.com/<numeric-id>/posts/<id>
      - Reel:  facebook.com/reel/<id>
      - Group: facebook.com/groups/<name>/posts/<id>
    """
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip("/")
    query = parsed.query.lower()

    if not _is_facebook_domain(url):
        return ContentSource.UNKNOWN

    if not path:
        return ContentSource.UNKNOWN

    # Groups
    if path.startswith("/groups/"):
        return ContentSource.FACEBOOK_GROUP

    # Reels
    if path.startswith("/reel/"):
        return ContentSource.FACEBOOK_POST  # reels are treated as video posts

    # Posts
    if "/posts/" in path:
        return ContentSource.FACEBOOK_POST

    if "/story.php" in path and "story_fbid" in query:
        return ContentSource.FACEBOOK_POST

    if path.startswith("/share/"):
        return ContentSource.FACEBOOK_POST

    if "/photo.php" in path and "fbid" in query:
        return ContentSource.FACEBOOK_POST

    # Pages (single-segment path like /page-name)
    parts = [p for p in path.split("/") if p]
    if len(parts) == 1 and not any(
        parts[0].startswith(prefix)
        for prefix in ("share", "reel", "story.php", "photo.php", "groups")
    ):
        return ContentSource.FACEBOOK_PAGE

    return ContentSource.UNKNOWN


def is_facebook_post_url(url: str) -> bool:
    """Return True if the URL points to a single Facebook post/reel."""
    return classify_facebook_url(url) == ContentSource.FACEBOOK_POST


def is_facebook_page_url(url: str) -> bool:
    """Return True if the URL points to a Facebook page."""
    return classify_facebook_url(url) == ContentSource.FACEBOOK_PAGE


def is_facebook_group_url(url: str) -> bool:
    """Return True if the URL points to a Facebook group."""
    return classify_facebook_url(url) == ContentSource.FACEBOOK_GROUP


def is_facebook_reel_url(url: str) -> bool:
    """Return True if the URL points to a Facebook Reel."""
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip("/")
    return path.startswith("/reel/")
