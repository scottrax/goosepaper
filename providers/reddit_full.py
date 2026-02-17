import datetime
import re
import html
import requests
import feedparser
import bs4
from typing import List

from goosepaper.storyprovider.storyprovider import StoryProvider
from goosepaper.story import Story
from goosepaper.util import PlacementPreference


class RedditFullStoryProvider(StoryProvider):
    """Reddit provider that fetches post content, selftext, and images."""

    def __init__(
        self,
        subreddit: str,
        limit: int = 5,
        since_days_ago: int = None,
        max_paragraphs: int = 4,
        max_chars: int = 900,
    ):
        self.limit = limit
        self.max_paragraphs = max_paragraphs
        self.max_chars = max_chars
        self._since = (
            datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
            if since_days_ago
            else None
        )
        subreddit = subreddit.lstrip("/")
        subreddit = subreddit[2:] if subreddit.startswith("r/") else subreddit
        self.subreddit = subreddit

    def _fetch_json(self):
        """Fetch subreddit posts via Reddit JSON API."""
        url = f"https://www.reddit.com/r/{self.subreddit}/hot.json?limit={self.limit + 5}"
        headers = {"User-Agent": "Goosepaper/1.0 (news reader)"}
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Reddit JSON API error for r/{self.subreddit}: {e}")
            return None

    def _clean_selftext(self, text: str) -> str:
        """Clean up Reddit selftext markdown into simple HTML."""
        if not text or text.strip() == "":
            return ""
        # Basic markdown-to-html: paragraphs
        paragraphs = text.strip().split("\n\n")
        html_parts = []
        total_chars = 0
        truncated = False
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            # Skip very short fragments
            if len(p) < 10:
                continue
            # Convert markdown links [text](url) to just text
            p = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", p)
            # Convert **bold** and *italic*
            p = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", p)
            p = re.sub(r"\*(.+?)\*", r"<i>\1</i>", p)
            # Remove remaining markdown artifacts
            p = re.sub(r"^#+\s*", "", p)
            p = re.sub(r"^[\-\*]\s+", "", p)
            plain_len = len(re.sub(r"<[^>]+>", "", p))
            if total_chars + plain_len > self.max_chars:
                remaining = self.max_chars - total_chars
                if remaining > 80:
                    short_p = p[:remaining].rsplit(" ", 1)[0].rstrip() + "..."
                    html_parts.append(f"<p>{short_p}</p>")
                truncated = True
                break
            html_parts.append(f"<p>{p}</p>")
            total_chars += plain_len
            if len(html_parts) >= self.max_paragraphs:
                truncated = True
                break
        if truncated:
            html_parts.append('<p><i>[Post truncated for print layout]</i></p>')
        return "".join(html_parts)

    def _normalize_image_url(self, url: str) -> str:
        if not url:
            return ""
        # Reddit preview/gallery URLs often encode entities.
        cleaned = html.unescape(url).replace("\\u0026", "&")
        if cleaned.startswith("//"):
            cleaned = f"https:{cleaned}"
        return cleaned

    def _looks_like_image_url(self, url: str) -> bool:
        if not url:
            return False
        if re.search(r"\.(jpg|jpeg|png|gif|webp)(\?.*)?$", url, re.IGNORECASE):
            return True
        # Common reddit/static image hosts
        return bool(
            re.search(
                r"(i\.redd\.it|preview\.redd\.it|i\.imgur\.com|redditmedia\.com)",
                url,
                re.IGNORECASE,
            )
        )

    def _collect_image_urls(self, post: dict) -> List[str]:
        candidates = []

        direct = self._normalize_image_url(post.get("url_overridden_by_dest", "") or post.get("url", ""))
        if direct and self._looks_like_image_url(direct):
            candidates.append(direct)

        preview = post.get("preview", {})
        for img in preview.get("images", []):
            source = self._normalize_image_url(img.get("source", {}).get("url", ""))
            if source:
                candidates.append(source)

        # Reddit gallery posts store image links in media_metadata.
        gallery_items = post.get("gallery_data", {}).get("items", [])
        media_meta = post.get("media_metadata", {})
        for item in gallery_items:
            media_id = item.get("media_id")
            if not media_id:
                continue
            metadata = media_meta.get(media_id, {})
            if metadata.get("status") != "valid":
                continue
            source = metadata.get("s", {})
            for key in ("u", "gif"):
                img_url = self._normalize_image_url(source.get(key, ""))
                if img_url:
                    candidates.append(img_url)
                    break

        # Some image posts are crossposts with media on the parent.
        for cross in post.get("crosspost_parent_list", [])[:1]:
            cross_url = self._normalize_image_url(cross.get("url_overridden_by_dest", "") or cross.get("url", ""))
            if cross_url:
                candidates.append(cross_url)
            cross_preview = cross.get("preview", {})
            for img in cross_preview.get("images", []):
                source = self._normalize_image_url(img.get("source", {}).get("url", ""))
                if source:
                    candidates.append(source)

        deduped = []
        seen = set()
        for url in candidates:
            if not url:
                continue
            if not self._looks_like_image_url(url):
                continue
            if url in seen:
                continue
            seen.add(url)
            deduped.append(url)
        return deduped

    def _clean_comment_text(self, text: str) -> str:
        if not text:
            return ""
        # Trim very long comments for print readability.
        text = text.strip()
        if len(text) > 1200:
            text = text[:1200].rsplit(" ", 1)[0].rstrip() + "..."

        # Basic markdown cleanup.
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[\-\*]\s+", "", text, flags=re.MULTILINE)

        chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
        html_parts = []
        for chunk in chunks[:3]:
            html_parts.append(f"<p>{chunk}</p>")
        return "".join(html_parts)

    def _fetch_comments_html(self, permalink: str, limit: int = 8) -> str:
        if not permalink:
            return ""
        url = f"https://www.reddit.com{permalink}.json?sort=top&limit={limit}"
        headers = {"User-Agent": "Goosepaper/1.0 (news reader)"}
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            return ""

        if not isinstance(payload, list) or len(payload) < 2:
            return ""

        comments_listing = payload[1].get("data", {}).get("children", [])
        comment_rows = []
        for child in comments_listing:
            if child.get("kind") != "t1":
                continue
            data = child.get("data", {})
            author = data.get("author", "[deleted]")
            score = data.get("score", 0)
            body_html = self._clean_comment_text(data.get("body", ""))
            if not body_html:
                continue
            comment_rows.append((author, score, body_html))
            if len(comment_rows) >= limit:
                break

        if not comment_rows:
            return "<p><i>No comment text available for this post.</i></p>"

        items = []
        for idx, (author, score, body_html) in enumerate(comment_rows, start=1):
            items.append(
                '<div class="comment-item" style="margin-bottom: 0.7em; padding-bottom: 0.4em; border-bottom: 1px dotted #999;">'
                f'<p style="margin: 0 0 0.2em 0;"><strong>{idx}. u/{author}</strong> · ▲ {score}</p>'
                f"{body_html}"
                "</div>"
            )
        return "".join(items)

    def get_stories(self, limit: int = 10, **kwargs) -> List[Story]:
        data = self._fetch_json()

        # Fallback to RSS if JSON fails
        if not data:
            return self._fallback_rss(limit)

        stories = []
        children = data.get("data", {}).get("children", [])

        for child in children:
            post = child.get("data", {})

            # Skip stickied/pinned posts
            if post.get("stickied", False):
                continue

            title = post.get("title", "")
            author = post.get("author", "A Reddit user")
            selftext = post.get("selftext", "")
            url = post.get("url", "")
            permalink = post.get("permalink", "")
            post_id = post.get("id", "")
            score = post.get("score", 0)
            num_comments = post.get("num_comments", 0)

            # Parse date
            created_utc = post.get("created_utc", 0)
            date = datetime.datetime.utcfromtimestamp(created_utc) if created_utc else None

            if self._since is not None and date and date < self._since:
                continue

            # Build body HTML
            body_parts = []

            # Add up to 2 images from direct/preview/gallery fields.
            image_urls = self._collect_image_urls(post)
            for img_url in image_urls[:2]:
                body_parts.append(
                    '<div style="text-align: center; margin: 0.2em 0 0.4em 0;">'
                    f'<img src="{img_url}" style="max-width: 100%; max-height: 340px;" />'
                    "</div>"
                )

            # Add selftext content
            if selftext:
                clean = self._clean_selftext(selftext)
                if clean:
                    body_parts.append(clean)

            # If it's a link post (not self, not image), mention the link domain
            is_self = post.get("is_self", False)
            if not is_self and not body_parts:
                domain = post.get("domain", "")
                if domain:
                    body_parts.append(f"<p><i>Link: {domain}</i></p>")

            # Add post stats
            body_parts.append(
                f'<p style="font-size: 8pt; color: #888;">'
                f'\u25b2 {score} points \u2022 {num_comments} comments</p>'
            )

            comments_anchor = ""
            comments_html = ""
            if permalink:
                comments_html = self._fetch_comments_html(permalink, limit=8)
                if comments_html:
                    comments_anchor = f"comments-{self.subreddit}-{post_id or len(stories)}"
                    body_parts.append(
                        '<p style="margin-top: 0.3em;">'
                        f'<a href="#{comments_anchor}">View comments \u2192</a>'
                        "</p>"
                    )

            body_html = "".join(body_parts) if body_parts else "<p></p>"

            story = Story(
                headline=title,
                body_html=body_html,
                byline=f"u/{author} in r/{self.subreddit}",
                date=date,
                placement_preference=PlacementPreference.NONE,
            )
            if comments_anchor and comments_html:
                story._comments_anchor = comments_anchor
                story._comments_html = comments_html
                story._comments_title = title
                story._comments_byline = f"Top comments from r/{self.subreddit}"
                story._comments_permalink = f"https://www.reddit.com{permalink}"

            stories.append(story)

            if len(stories) >= min(self.limit, limit):
                break

        return stories

    def _fallback_rss(self, limit: int) -> List[Story]:
        """Fallback to RSS feed if JSON API fails."""
        feed = feedparser.parse(f"https://www.reddit.com/r/{self.subreddit}.rss")
        limit = min(self.limit, len(feed.entries), limit)
        stories = []
        for entry in feed.entries:
            try:
                author = entry.author
            except AttributeError:
                author = "A Reddit user"

            date = datetime.datetime(*entry.updated_parsed[:6])
            if self._since is not None and date < self._since:
                continue

            # Try to extract content from RSS entry
            content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
            body_html = ""
            if content:
                soup = bs4.BeautifulSoup(content, "html.parser")
                # Reddit RSS wraps content in a table, extract useful parts
                for link_table in soup.find_all("table"):
                    link_table.decompose()
                text = soup.get_text(strip=True)
                if len(text) > 20:
                    body_html = str(soup)

            if not body_html:
                body_html = "<p></p>"

            stories.append(
                Story(
                    headline=str(entry.title),
                    body_html=body_html,
                    byline=f"{author} in r/{self.subreddit}",
                    date=date,
                    placement_preference=PlacementPreference.NONE,
                )
            )
            if len(stories) >= limit:
                break

        return stories
