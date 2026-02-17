import datetime
import re
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
            score = post.get("score", 0)
            num_comments = post.get("num_comments", 0)

            # Parse date
            created_utc = post.get("created_utc", 0)
            date = datetime.datetime.utcfromtimestamp(created_utc) if created_utc else None

            if self._since is not None and date and date < self._since:
                continue

            # Build body HTML
            body_parts = []

            # Add image if it's a direct image post
            if url and re.search(r"\.(jpg|jpeg|png|gif|webp)(\?.*)?$", url, re.IGNORECASE):
                body_parts.append(f'<div style="text-align: center;"><img src="{url}" style="max-width: 100%;" /></div>')

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

            body_html = "".join(body_parts) if body_parts else "<p></p>"

            stories.append(
                Story(
                    headline=title,
                    body_html=body_html,
                    byline=f"u/{author} in r/{self.subreddit}",
                    date=date,
                    placement_preference=PlacementPreference.NONE,
                )
            )

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
