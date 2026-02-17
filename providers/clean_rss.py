import datetime
import re
import requests
import feedparser
from typing import List
from readability import Document
import bs4

from goosepaper.storyprovider.storyprovider import StoryProvider
from goosepaper.story import Story

# Patterns that indicate broken/useless content
_JUNK_PATTERNS = [
    re.compile(r"you need javascript enabled", re.IGNORECASE),
    re.compile(r"please enable javascript", re.IGNORECASE),
    re.compile(r"this content is not available", re.IGNORECASE),
    re.compile(r"your browser does not support", re.IGNORECASE),
    re.compile(r"<video[\s>]", re.IGNORECASE),
    re.compile(r"<iframe[\s>]", re.IGNORECASE),
    re.compile(r"to watch this content", re.IGNORECASE),
    re.compile(r"video is not available", re.IGNORECASE),
    re.compile(r"subscribe to (read|watch|continue)", re.IGNORECASE),
    re.compile(r"sign in to continue", re.IGNORECASE),
]


def _clean_html_content(html: str) -> str:
    """Remove script, style, video, iframe, noscript tags and clean up."""
    soup = bs4.BeautifulSoup(html, "html.parser")

    # Remove unwanted tags entirely
    for tag_name in ["script", "style", "video", "iframe", "noscript", "svg",
                     "form", "input", "button", "nav", "footer", "aside",
                     "source", "picture"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove image caption/credit containers that have no actual images
    # These show up as orphaned "Image:" / "Pic: AP" text
    for tag in soup.find_all(attrs={"aria-label": re.compile(r"(image|photo)\s*(caption|credit)", re.IGNORECASE)}):
        tag.decompose()
    for tag in soup.find_all(class_=re.compile(r"(credit-caption|caption-wrap|credit|toggle-caption|enlarge|image-wrap|figure-wrap)", re.IGNORECASE)):
        # Only remove if there's no <img> inside
        if not tag.find("img"):
            tag.decompose()

    # Remove figure/figcaption elements that lost their images
    for tag in soup.find_all(["figure", "figcaption"]):
        if not tag.find("img"):
            tag.decompose()

    # Remove hidden elements
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none")):
        tag.decompose()

    # Remove empty divs/paragraphs
    for tag in soup.find_all(["div", "p", "span"]):
        if not tag.get_text(strip=True) and not tag.find("img"):
            tag.decompose()

    # Clean up orphaned caption-like text patterns in remaining content
    result = str(soup)
    # Remove lines that are just "Image:" or "Pic: <credit>" with nothing else useful
    result = re.sub(r"<p>\s*(Image|Pic|Photo|Credit|Caption)\s*:?\s*</p>", "", result, flags=re.IGNORECASE)
    result = re.sub(r"<b>\s*toggle caption\s*</b>", "", result, flags=re.IGNORECASE)
    result = re.sub(r"<b>\s*hide caption\s*</b>", "", result, flags=re.IGNORECASE)

    return result


def _is_junk(text: str) -> bool:
    """Check if content is mostly junk/placeholder text."""
    for pattern in _JUNK_PATTERNS:
        if pattern.search(text):
            return True
    # If the visible text is very short, it's probably not a real article
    clean = re.sub(r"<[^>]+>", "", text).strip()
    if len(clean) < 50:
        return True
    return False


def _is_video_entry(entry) -> bool:
    """Check if an RSS entry is a video rather than an article."""
    # Check media content
    media = entry.get("media_content", [])
    for m in media:
        if "video" in m.get("type", ""):
            return True
    # Check link for video indicators
    link = entry.get("link", "")
    if "/video/" in link or "/videos/" in link or "/watch/" in link:
        return True
    # Check tags/categories
    tags = entry.get("tags", [])
    for tag in tags:
        term = tag.get("term", "").lower()
        if term in ("video", "videos", "multimedia"):
            return True
    return False


class CleanRSSFeedStoryProvider(StoryProvider):
    def __init__(
        self,
        rss_path: str,
        name: str = "",
        limit: int = 5,
        since_days_ago: int = None,
    ) -> None:
        self.limit = limit
        self.feed_url = rss_path
        self.name = name
        self._since = (
            datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
            if since_days_ago
            else None
        )

    def get_stories(self, limit: int = 5, **kwargs) -> List[Story]:
        feed = feedparser.parse(self.feed_url)
        limit = min(limit, self.limit, len(feed.entries))
        if limit == 0:
            print(f"Sad honk :/ No entries found for feed {self.feed_url}...")
            return []

        source_name = self.name or feed.feed.get("title", "")
        if not source_name:
            source_name = self.feed_url.split("/")[2] if "/" in self.feed_url else "RSS"

        stories = []
        for entry in feed.entries:
            # Skip video entries
            if _is_video_entry(entry):
                continue

            # Parse date
            date = None
            for date_field in ("updated_parsed", "published_parsed"):
                parsed = entry.get(date_field)
                if parsed:
                    try:
                        date = datetime.datetime(*parsed[:6])
                    except (TypeError, ValueError):
                        pass
                    break

            if self._since is not None and date and date < self._since:
                continue

            title = entry.get("title", "")
            link = entry.get("link", "")

            # Try to fetch full article
            body_html = ""
            try:
                req = requests.get(link, timeout=8, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Goosepaper/1.0)"
                })
                if req.ok:
                    doc = Document(req.content)
                    extracted = doc.summary()
                    cleaned = _clean_html_content(extracted)

                    if not _is_junk(cleaned):
                        body_html = cleaned
                        title = doc.title() or title
            except Exception:
                pass

            # Fall back to RSS description if full article failed
            if not body_html:
                desc = entry.get("description", entry.get("summary", ""))
                if desc:
                    cleaned = _clean_html_content(desc)
                    if not _is_junk(cleaned):
                        body_html = cleaned

            # Skip entries with no usable content
            if not body_html:
                continue

            stories.append(
                Story(
                    headline=title,
                    body_html=body_html,
                    byline=source_name,
                    date=date,
                )
            )
            if len(stories) >= limit:
                break

        return stories
