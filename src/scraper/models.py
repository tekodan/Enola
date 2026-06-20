"""Models for scraper module."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ContentSource(StrEnum):
    """Source type for scraped content."""

    FACEBOOK_PAGE = "facebook_page"
    FACEBOOK_GROUP = "facebook_group"
    FACEBOOK_POST = "facebook_post"
    UNKNOWN = "unknown"


class Post(BaseModel):
    """Model representing a Facebook post.

    Attributes:
        id: Unique identifier for the post
        text: Full text content of the post
        author: Name of the author/page
        date: Publication date
        likes: Number of likes
        comments_count: Number of comments
        shares: Number of shares
        url: Full URL to the post
        page_id: ID of the page that posted it
        source: Type of content source
        reactions: Dictionary of reaction counts by type
        media_urls: List of media URLs in the post
        created_at: Timestamp when data was scraped
    """

    id: str
    text: str = ""
    author: str = ""
    date: datetime | None = None
    likes: int = 0
    comments_count: int = 0
    shares: int = 0
    url: str | None = None
    page_id: str | None = None
    source: ContentSource = ContentSource.FACEBOOK_PAGE
    reactions: dict = Field(default_factory=dict)
    media_urls: list[str] = Field(default_factory=list)
    comments: list["Comment"] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("likes", "comments_count", "shares", mode="before")
    @classmethod
    def validate_counts(cls, v):
        """Ensure counts are non-negative integers."""
        if v is None:
            return 0
        if isinstance(v, str):
            return int(v) if v.isdigit() else 0
        return max(0, int(v))

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "text": self.text,
            "author": self.author,
            "date": self.date.isoformat() if self.date else None,
            "likes": self.likes,
            "comments_count": self.comments_count,
            "shares": self.shares,
            "url": self.url,
            "page_id": self.page_id,
            "source": self.source.value,
            "reactions": self.reactions,
            "media_urls": self.media_urls,
            "created_at": self.created_at.isoformat(),
        }

    def has_text(self) -> bool:
        """Check if post has text content."""
        return bool(self.text and self.text.strip())

    def get_engagement(self) -> int:
        """Calculate total engagement score."""
        return self.likes + self.comments_count + self.shares


class Comment(BaseModel):
    """Model representing a Facebook comment.

    Attributes:
        id: Unique identifier for the comment
        text: Full text content of the comment
        author: Name of the commenter
        date: Publication date
        likes: Number of likes on comment
        post_id: ID of the parent post
        parent_id: ID of parent comment (for replies)
        url: Full URL to the comment
        created_at: Timestamp when data was scraped
    """

    id: str
    text: str = ""
    author: str = ""
    date: datetime | None = None
    likes: int = 0
    post_id: str | None = None
    parent_id: str | None = None
    url: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("likes", mode="before")
    @classmethod
    def validate_likes(cls, v):
        """Ensure likes is non-negative integer."""
        if v is None:
            return 0
        if isinstance(v, str):
            return int(v) if v.isdigit() else 0
        return max(0, int(v))

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "text": self.text,
            "author": self.author,
            "date": self.date.isoformat() if self.date else None,
            "likes": self.likes,
            "post_id": self.post_id,
            "parent_id": self.parent_id,
            "url": self.url,
            "created_at": self.created_at.isoformat(),
        }

    def is_reply(self) -> bool:
        """Check if comment is a reply to another comment."""
        return self.parent_id is not None

    def has_text(self) -> bool:
        """Check if comment has text content."""
        return bool(self.text and self.text.strip())


class PageInfo(BaseModel):
    """Model representing information about a Facebook page.

    Attributes:
        id: Unique identifier for the page
        name: Name of the page
        url: URL to the page
        likes: Number of page likes
        description: Page description
        category: Page category
        is_public: Whether the page is public
        scraped_at: Timestamp when data was scraped
    """

    id: str
    name: str = ""
    url: str | None = None
    likes: int = 0
    description: str = ""
    category: str = ""
    is_public: bool = True
    scraped_at: datetime = Field(default_factory=datetime.now)

    @field_validator("likes", mode="before")
    @classmethod
    def validate_likes(cls, v):
        """Ensure likes is non-negative integer."""
        if v is None:
            return 0
        if isinstance(v, str):
            return int(v) if v.isdigit() else 0
        return max(0, int(v))

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "likes": self.likes,
            "description": self.description,
            "category": self.category,
            "is_public": self.is_public,
            "scraped_at": self.scraped_at.isoformat(),
        }


class GroupInfo(BaseModel):
    """Model representing information about a Facebook group.

    Attributes:
        id: Unique identifier for the group
        name: Name of the group
        url: URL to the group
        members: Number of members
        description: Group description
        privacy: Privacy setting (public, private, etc.)
        scraped_at: Timestamp when data was scraped
    """

    id: str
    name: str = ""
    url: str | None = None
    members: int = 0
    description: str = ""
    privacy: str = "public"
    scraped_at: datetime = Field(default_factory=datetime.now)

    @field_validator("members", mode="before")
    @classmethod
    def validate_members(cls, v):
        """Ensure members is non-negative integer."""
        if v is None:
            return 0
        if isinstance(v, str):
            return int(v) if v.isdigit() else 0
        return max(0, int(v))

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "members": self.members,
            "description": self.description,
            "privacy": self.privacy,
            "scraped_at": self.scraped_at.isoformat(),
        }


class ScrapeResult(BaseModel):
    """Result of a scraping operation.

    Attributes:
        success: Whether the scraping was successful
        posts: List of extracted posts
        comments: List of extracted comments
        pages: List of discovered pages
        errors: List of error messages
        pages_scraped: Number of pages scraped
        posts_found: Number of posts found
        comments_found: Number of comments found
    """

    success: bool
    posts: list[Post] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)
    pages: list[PageInfo] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    pages_scraped: int = 0
    posts_found: int = 0
    comments_found: int = 0

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def merge(self, other: "ScrapeResult") -> None:
        """Merge another scrape result into this one."""
        self.posts.extend(other.posts)
        self.comments.extend(other.comments)
        self.pages.extend(other.pages)
        self.errors.extend(other.errors)
        self.pages_scraped += other.pages_scraped
        self.posts_found += other.posts_found
        self.comments_found += other.comments_found

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def total_items(self) -> int:
        """Total number of items scraped."""
        return len(self.posts) + len(self.comments) + len(self.pages)
