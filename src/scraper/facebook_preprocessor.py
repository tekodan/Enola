"""Facebook HTML preprocessor to extract hierarchical structure.

Preprocesses raw Facebook HTML to extract:
- Page metadata (title, URL)
- Posts with text, author, date, likes, comments_count, shares
- Comments with text, author, date, likes

Reduces HTML size significantly before sending to LLM.
"""

import logging
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FacebookPreprocessor:
    """Preprocess Facebook HTML to extract structured content."""

    @staticmethod
    def extract_page_metadata(html: str, url: str) -> dict[str, Any]:
        """Extract page-level metadata from Facebook HTML.
        
        Returns:
            Dict with page title, url, post_count, etc.
        """
        soup = BeautifulSoup(html, "html.parser")

        result = {
            "url": url,
            "title": "",
            "post_count": 0,
            "metadata": {}
        }

        # Try to extract page title
        title_tag = soup.find("title")
        if title_tag:
            result["title"] = title_tag.get_text(strip=True)

        # Look for meta tags
        for meta in soup.find_all("meta"):
            if meta.get("property") == "og:title":
                result["metadata"]["og_title"] = meta.get("content", "")
            elif meta.get("property") == "og:description":
                result["metadata"]["og_description"] = meta.get("content", "")
            elif meta.get("property") == "og:site_name":
                result["metadata"]["site_name"] = meta.get("content", "")

        return result

    @staticmethod
    def extract_posts(html: str, base_url: str) -> list[dict[str, Any]]:
        """Extract posts from Facebook HTML using DOM patterns.
        
        Facebook posts typically have:
        - Data attributes like `data-testid="post_message"`
        - CSS classes with "userContent", "x1e56ztr", "x1xmf6yo"
        - Structured data in meta tags
        
        Args:
            html: Raw Facebook HTML
            base_url: Base URL for constructing absolute URLs
            
        Returns:
            List of post dictionaries with structure:
            {
                "text": "post content",
                "author": "author name",
                "date": "2024-01-01",
                "likes": 42,
                "comments_count":的大量,
                "shares":大量,
                "url": "full_post_url"
            }
        """
        soup = BeautifulSoup(html, "html.parser")
        posts = []

        # Strategy 1: Find posts by aria-label (modern Facebook)
        # Pattern: "Acciones en esta publicación de [Author]" or "Publicación de [Author]"
        import re
        post_anchors = soup.find_all(
            'div',
            attrs={'aria-label': re.compile(r'(publicaci.n de|Acciones en esta)', re.IGNORECASE)}
        )

        logger.debug("Found %d post anchors via aria-label", len(post_anchors))

        for idx, anchor in enumerate(post_anchors):
            try:
                post_data = FacebookPreprocessor._parse_post_by_anchor(anchor, idx, base_url)
                if post_data:
                    posts.append(post_data)
            except Exception as e:
                logger.debug("Failed to parse post anchor %d: %s", idx, e)

        # Strategy 2: Look for post_message data-testid (fallback)
        if not posts:
            post_elements = soup.find_all(attrs={"data-testid": "post_message"})
            for idx, post_elem in enumerate(post_elements):
                try:
                    post_data = FacebookPreprocessor._parse_post_element(post_elem, idx, base_url)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.debug("Failed to parse post element %d: %s", idx, e)

        # Strategy 2: Look for userContent class (older Facebook)
        if not posts:
            user_content = soup.find_all(class_="userContent")
            for idx, elem in enumerate(user_content):
                try:
                    post_data = FacebookPreprocessor._parse_user_content(elem, idx, base_url)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.debug("Failed to parse userContent %d: %s", idx, e)

        # Strategy 3: Look for common Facebook post patterns
        if not posts:
            # Try to find divs with aria-label containing "Publicación"
            for elem in soup.find_all(attrs={"aria-label": lambda x: x and "Publicación" in x}):
                try:
                    post_data = FacebookPreprocessor._parse_generic_post(elem, len(posts), base_url)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.debug("Failed to parse generic post: %s", e)

        logger.info("Extracted %d posts from HTML", len(posts))
        return posts

    @staticmethod
    def _parse_post_by_anchor(anchor, idx: int, base_url: str) -> dict[str, Any] | None:
        """Parse a Facebook post using its aria-label anchor.
        
        Goes up the DOM tree to find the full post container with all content.
        """
        import re

        # Go up a FIXED number of levels to find the post container
        # Going too far captures multiple posts; staying too close loses content
        container = anchor
        for level in range(8):
            parent = container.parent
            if not parent or parent.name == 'body':
                break
            container = parent

        full_text = container.get_text(' ', strip=True)

        if len(full_text) < 30:
            return None

        # Extract author from aria-label of the anchor
        author = "Unknown"
        aria_label = anchor.get('aria-label', '')
        match = re.search(r'publicaci[óo]n de ([^"]+?)(?:"|$)', aria_label, re.IGNORECASE)
        if match:
            author = match.group(1).strip()

        # Extract date from relative time patterns
        date_str = ""
        relative_patterns = [
            r'(\d+)\s*h\b',
            r'(\d+)\s*min\b',
            r'(\d+)\s*d[ií]as?',
            r'(\d+)\s*sem',
        ]
        for pattern in relative_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                break

        # Extract likes count
        likes = 0
        like_patterns = [
            r'(\d+)\s*reacciones?',
            r'(\d+)\s*me gusta',
            r'(\d+)\s*likes?',
        ]
        for pattern in like_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                likes = int(match.group(1))
                break

        # Extract comments count
        comments_count = 0
        comment_patterns = [
            r'(\d+)\s*comentarios?',
        ]
        for pattern in comment_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                comments_count = int(match.group(1))
                break

        # Extract shares count
        shares = 0
        share_patterns = [
            r'(\d+)\s*compartidos?',
            r'(\d+)\s*veces compartido',
        ]
        for pattern in share_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                shares = int(match.group(1))
                break

        # Clean up text aggressively
        clean_text = full_text

        # Remove leading "Facebook" repetitions (navigation noise)
        clean_text = re.sub(r'^(Facebook\s*){2,}', '', clean_text)

        # Remove the "scrambled text" pattern (single chars separated by spaces)
        # Pattern: "o d S o p s r t e n l 3 h"
        # This is Facebook's anti-scraping obfuscation
        # Match sequences of single characters/digits separated by spaces
        clean_text = re.sub(
            r'(?:\s+[a-zA-Z0-9]\s*){5,}',
            ' ',
            clean_text
        )

        # Remove "Compartido con: Público" marker
        clean_text = re.sub(r'\s*Compartido con:\s*P[úu]blico\s*', ' ', clean_text)

        # Remove the author name at the start (we already have it)
        if author != "Unknown":
            clean_text = re.sub(r'^' + re.escape(author) + r'\s*', '', clean_text)

        # Remove duplicate consecutive words
        words = clean_text.split()
        deduped_words = []
        for word in words:
            if not deduped_words or deduped_words[-1] != word or len(word) > 5:
                deduped_words.append(word)
        clean_text = ' '.join(deduped_words)

        # Collapse whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        # Construct post URL
        post_url = f"{base_url}#post_{idx}"

        return {
            "text": clean_text,
            "author": author,
            "date": date_str,
            "likes": likes,
            "comments_count": comments_count,
            "shares": shares,
            "url": post_url
        }

    @staticmethod
    def _parse_post_element(elem, idx: int, base_url: str) -> dict[str, Any] | None:
        """Parse a Facebook post element with data-testid="post_message"."""
        # Get text content
        text = elem.get_text(strip=True)
        if not text or len(text) < 10:
            return None

        # Try to find author in parent hierarchy
        author = ""
        parent = elem.parent
        for _ in range(5):  # Look up to 5 levels
            if parent:
                # Look for author name in links or spans
                author_link = parent.find("a", href=lambda x: x and "/" in x)
                if author_link:
                    author = author_link.get_text(strip=True)
                    break
                parent = parent.parent

        # Try to find date
        date_str = ""
        time_elem = elem.find_next("time")
        if time_elem and time_elem.get("datetime"):
            date_str = time_elem.get("datetime")
        elif time_elem:
            date_str = time_elem.get_text(strip=True)

        # Try to find likes/comments
        likes = 0
        comments_count = 0
        shares = 0

        # Look for reaction text
        reactions_text = ""
        reactions_elem = elem.find_next(string=lambda x: x and ("reacción" in x.lower() or "like" in x.lower()))
        if reactions_elem:
            reactions_text = str(reactions_elem)
            import re
            like_match = re.search(r'(\d+)\s*(?:reacción|like)', reactions_text)
            if like_match:
                likes = int(like_match.group(1))

        # Look for comment count
        comments_elem = elem.find_next(string=lambda x: x and "comentario" in x.lower())
        if comments_elem:
            comments_text = str(comments_elem)
            import re
            comment_match = re.search(r'(\d+)\s*comentario', comments_text)
            if comment_match:
                comments_count = int(comment_match.group(1))

        # Construct post URL
        post_url = f"{base_url}#post_{idx}"

        # Parse date if possible
        parsed_date = FacebookPreprocessor._parse_fb_date(date_str)
        date_iso = parsed_date.strftime("%Y-%m-%d") if parsed_date else ""

        return {
            "text": text,
            "author": author or "Unknown",
            "date": date_iso,
            "likes": likes,
            "comments_count": comments_count,
            "shares": shares,
            "url": post_url
        }

    @staticmethod
    def _parse_user_content(elem, idx: int, base_url: str) -> dict[str, Any] | None:
        """Parse older Facebook userContent class posts."""
        text = elem.get_text(strip=True)
        if not text or len(text) < 10:
            return None

        # Find author in preceding elements
        author = "Unknown"
        prev_elem = elem.find_previous(class_=lambda x: x and "actor" in x.lower())
        if prev_elem:
            author_text = prev_elem.get_text(strip=True)
            if author_text and len(author_text) < 100:  # Reasonable author name length
                author = author_text

        # Find date
        date_str = ""
        time_elem = elem.find_previous("abbr")
        if time_elem and time_elem.get("data-utime"):
            date_str = time_elem.get("data-utime")

        post_url = f"{base_url}#post_{idx}"
        parsed_date = FacebookPreprocessor._parse_fb_date(date_str)
        date_iso = parsed_date.strftime("%Y-%m-%d") if parsed_date else ""

        return {
            "text": text,
            "author": author,
            "date": date_iso,
            "likes": 0,
            "comments_count": 0,
            "shares": 0,
            "url": post_url
        }

    @staticmethod
    def _parse_generic_post(elem, idx: int, base_url: str) -> dict[str, Any] | None:
        """Parse generic Facebook post using aria-label."""
        text = elem.get_text(strip=True)
        if not text or len(text) < 10:
            return None

        # Extract author from aria-label if present
        author = "Unknown"
        aria_label = elem.get("aria-label", "")
        if "Publicación de" in aria_label:
            # Example: "Publicación de Juan Pérez"
            import re
            match = re.search(r'Publicación de (.+)$', aria_label)
            if match:
                author = match.group(1).strip()

        post_url = f"{base_url}#post_{idx}"

        return {
            "text": text,
            "author": author,
            "date": "",
            "likes": 0,
            "comments_count": 0,
            "shares": 0,
            "url": post_url
        }

    @staticmethod
    def extract_comments(html: str, base_url: str) -> list[dict[str, Any]]:
        """Extract comments from Facebook HTML.
        
        Args:
            html: Raw Facebook HTML
            base_url: Base URL for constructing absolute URLs
            
        Returns:
            List of comment dictionaries with structure:
            {
                "text": "comment text",
                "author": "author name",
                "date": "2024-01-01",
                "likes": 5,
                "url": "full_comment_url"
            }
        """
        soup = BeautifulSoup(html, "html.parser")
        comments = []

        # Strategy 1: Look for comment data-testid
        comment_elements = soup.find_all(attrs={"data-testid": lambda x: x and "comment" in x.lower()})
        for idx, comment_elem in enumerate(comment_elements):
            try:
                comment_data = FacebookPreprocessor._parse_comment_element(comment_elem, idx, base_url)
                if comment_data:
                    comments.append(comment_data)
            except Exception as e:
                logger.debug("Failed to parse comment element %d: %s", idx, e)

        # Strategy 2: Look for reply text patterns
        if not comments:
            for elem in soup.find_all(string=lambda x: x and "Responder" in x):
                parent = elem.parent
                if parent:
                    # Look for comment text in siblings
                    comment_text = FacebookPreprocessor._find_comment_text_near(parent)
                    if comment_text:
                        comment_data = {
                            "text": comment_text,
                            "author": "Unknown",
                            "date": "",
                            "likes": 0,
                            "url": f"{base_url}#comment_{len(comments)}"
                        }
                        comments.append(comment_data)

        logger.info("Extracted %d comments from HTML", len(comments))
        return comments

    @staticmethod
    def _parse_comment_element(elem, idx: int, base_url: str) -> dict[str, Any] | None:
        """Parse a Facebook comment element."""
        text = elem.get_text(strip=True)
        if not text or len(text) < 5:
            return None

        # Try to find author
        author = "Unknown"
        author_elem = elem.find_previous(class_=lambda x: x and ("actor" in x.lower() or "author" in x.lower()))
        if author_elem:
            author_text = author_elem.get_text(strip=True)
            if author_text and len(author_text) < 100:
                author = author_text

        # Try to find date
        date_str = ""
        time_elem = elem.find_next("time")
        if time_elem and time_elem.get("datetime"):
            date_str = time_elem.get("datetime")

        parsed_date = FacebookPreprocessor._parse_fb_date(date_str)
        date_iso = parsed_date.strftime("%Y-%m-%d") if parsed_date else ""

        # Try to find likes
        likes = 0
        likes_elem = elem.find_next(string=lambda x: x and ("Like" in x or "Me gusta" in x))
        if likes_elem:
            likes_text = str(likes_elem)
            import re
            like_match = re.search(r'(\d+)', likes_text)
            if like_match:
                likes = int(like_match.group(1))

        return {
            "text": text,
            "author": author,
            "date": date_iso,
            "likes": likes,
            "url": f"{base_url}#comment_{idx}"
        }

    @staticmethod
    def _find_comment_text_near(elem) -> str:
        """Find comment text near an element with 'Responder' text."""
        # Look for text in previous siblings
        prev_sibling = elem.previous_sibling
        while prev_sibling:
            if hasattr(prev_sibling, 'get_text'):
                text = prev_sibling.get_text(strip=True)
                if text and len(text) > 10:
                    return text
            prev_sibling = prev_sibling.previous_sibling

        # Look in parent
        if elem.parent and hasattr(elem.parent, 'get_text'):
            text = elem.parent.get_text(strip=True)
            if text and len(text) > 10:
                return text

        return ""

    @staticmethod
    def _parse_fb_date(date_str: str) -> datetime | None:
        """Parse Facebook date string in various formats."""
        if not date_str:
            return None

        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        try:
            # Try timestamp
            return datetime.fromtimestamp(int(date_str))
        except (ValueError, TypeError):
            pass

        # Try common Spanish date formats
        formats = [
            "%d de %B de %Y",  # "15 de enero de 2024"
            "%d/%m/%Y",        # "15/01/2024"
            "%Y-%m-%d",        # "2024-01-15"
            "%B %d, %Y",       # "January 15, 2024"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def create_hierarchical_json(html: str, url: str) -> dict[str, Any]:
        """Create hierarchical JSON structure from Facebook HTML.
        
        Returns:
            {
                "page": {
                    "title": "Page Title",
                    "url": "https://facebook.com/...",
                    "metadata": {...}
                },
                "posts": [
                    {
                        "text": "post content",
                        "author": "author",
                        "date": "2024-01-01",
                        "likes": 大量,
                        "comments_count": 大量,
                        "shares": 大量,
                        "url": "post_url",
                        "comments": [
                            {
                                "text": "comment text",
                                "author": "commenter",
                                "date": "2024-01-01",
                                "likes": 5,
                                "url": "comment_url"
                            }
                        ]
                    }
                ]
            }
        """
        page_meta = FacebookPreprocessor.extract_page_metadata(html, url)
        posts = FacebookPreprocessor.extract_posts(html, url)
        all_comments = FacebookPreprocessor.extract_comments(html, url)

        # For simplicity, attach all comments to first post
        # In a real implementation, we'd match comments to posts
        if posts and all_comments:
            posts[0]["comments"] = all_comments

        return {
            "page": page_meta,
            "posts": posts
        }

    @staticmethod
    def preprocess_for_llm(html: str, url: str) -> str:
        """Preprocess HTML for LLM consumption.
        
        Creates a clean, structured text representation with hierarchy.
        """
        hierarchical = FacebookPreprocessor.create_hierarchical_json(html, url)

        # Convert to readable text format
        lines = []

        # Page info
        lines.append(f"PÁGINA: {hierarchical['page']['title']}")
        lines.append(f"URL: {hierarchical['page']['url']}")
        lines.append("=" * 50)

        # Posts
        for i, post in enumerate(hierarchical["posts"], 1):
            lines.append(f"\nPUBLICACIÓN {i}:")
            lines.append(f"Autor: {post.get('author', 'Desconocido')}")
            lines.append(f"Fecha: {post.get('date', 'Desconocida')}")
            lines.append(f"Likes: {post.get('likes', 0)}")
            lines.append(f"Comentarios: {post.get('comments_count', 0)}")
            lines.append(f"Compartidos: {post.get('shares', 0)}")
            lines.append("-" * 40)
            lines.append(f"Texto:\n{post.get('text', '')}")

            # Comments for this post
            if "comments" in post:
                lines.append(f"\n  COMENTARIOS ({len(post['comments'])}):")
                for j, comment in enumerate(post["comments"], 1):
                    lines.append(f"    {j}. {comment.get('author', 'Anónimo')}: {comment.get('text', '')[:100]}...")
                    lines.append(f"      Likes: {comment.get('likes', 0)}, Fecha: {comment.get('date', '')}")

        return "\n".join(lines)

    @staticmethod
    def reduce_html_size(html: str, max_chars: int = 50000) -> str:
        """Reduce HTML size by removing unnecessary elements.
        
        Args:
            html: Raw HTML
            max_chars: Maximum characters to keep
            
        Returns:
            Reduced HTML string
        """
        if len(html) <= max_chars:
            return html

        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style tags
        for tag in soup(["script", "style", "iframe", "noscript"]):
            tag.decompose()

        # Remove meta tags except useful ones
        keep_meta = ["og:title", "og:description", "og:site_name"]
        for meta in soup.find_all("meta"):
            prop = meta.get("property", "")
            if prop not in keep_meta:
                meta.decompose()

        # Remove links to external resources
        for link in soup.find_all("link"):
            if link.get("rel") != ["stylesheet"]:
                link.decompose()

        # Keep only body content if it's still too large
        result = str(soup)
        if len(result) > max_chars:
            # Extract just the body
            body = soup.find("body")
            if body:
                result = str(body)

        # Truncate if still too long
        if len(result) > max_chars:
            result = result[:max_chars] + "... [TRUNCATED]"

        logger.info("Reduced HTML from %d to %d chars", len(html), len(result))
        return result
