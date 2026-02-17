"""
Patched version of goosepaper/goosepaper.py that adds:
- Section anchors (id attributes) on each story provider's content
- A minimal TOC/nav header with clickable links to sections
"""

import pathlib
from typing import List, Optional, Type, Union
import datetime
import io
import tempfile
from uuid import uuid4
from collections import OrderedDict

from goosepaper.story import Story
from goosepaper.styles import Style
from goosepaper.util import PlacementPreference
from goosepaper.storyprovider.storyprovider import StoryProvider


def _get_style(style):
    if isinstance(style, str):
        style_obj = Style(style)
    else:
        try:
            style_obj = style()
        except Exception as e:
            raise ValueError(f"Invalid style {style}") from e
    return style_obj


def _slugify(text):
    import re
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug


class Goosepaper:
    def __init__(
        self,
        story_providers: List[StoryProvider],
        title: str = None,
        subtitle: str = None,
        sections: List[dict] = None,
    ):
        self.story_providers = story_providers
        self.title = title if title else "Daily Goosepaper"
        self.subtitle = subtitle + "\n" if subtitle else ""
        self.subtitle += datetime.datetime.today().strftime("%B %d, %Y %H:%M")
        self.sections = sections or []

    def get_stories(self, deduplicate: bool = False) -> List[Story]:
        stories: List[Story] = []
        for prov in self.story_providers:
            new_stories = prov.get_stories()
            for a in new_stories:
                if deduplicate:
                    for b in stories:
                        if a.headline == b.headline and a.date == b.date:
                            break
                    else:
                        stories.append(a)
                else:
                    stories.append(a)
        return stories

    def _get_stories_by_provider(self):
        """Get stories grouped by provider, preserving order."""
        grouped = []
        for i, prov in enumerate(self.story_providers):
            stories = prov.get_stories()
            if stories:
                grouped.append((i, prov, stories))
        return grouped

    def _provider_section_name(self, prov, index):
        """Derive a human-readable section name from a provider."""
        cls_name = prov.__class__.__name__
        name_map = {
            "FiveDayForecastProvider": "Weather",
            "OpenMeteoWeatherStoryProvider": "Weather",
            "CleanRSSFeedStoryProvider": getattr(prov, "name", "") or "News",
            "RSSFeedStoryProvider": "News",
            "WikipediaCurrentEventsStoryProvider": "Current Events",
            "XKCDStoryProvider": "XKCD",
            "NasaApodStoryProvider": "NASA APOD",
            "WordSearchStoryProvider": "Word Search",
            "CrosswordStoryProvider": "Crossword",
            "RedditHeadlineStoryProvider": f"r/{getattr(prov, 'subreddit', 'reddit')}",
            "RedditFullStoryProvider": f"r/{getattr(prov, 'subreddit', 'reddit')}",
        }
        return name_map.get(cls_name, cls_name.replace("StoryProvider", "").replace("Provider", ""))

    # Provider class names that count as "games" — always rendered last
    _GAME_PROVIDERS = {
        "WordSearchStoryProvider",
        "CrosswordStoryProvider",
    }
    _REDDIT_PROVIDERS = {
        "RedditHeadlineStoryProvider",
        "RedditFullStoryProvider",
    }

    def _is_game_provider(self, prov):
        return prov.__class__.__name__ in self._GAME_PROVIDERS

    def _is_reddit_provider(self, prov):
        return prov.__class__.__name__ in self._REDDIT_PROVIDERS

    def to_html(self) -> str:
        grouped = self._get_stories_by_provider()

        # Sort: non-games first (in config order), then games last
        non_games = [(i, p, s) for i, p, s in grouped if not self._is_game_provider(p)]
        games = [(i, p, s) for i, p, s in grouped if self._is_game_provider(p)]
        grouped = non_games + games

        # Build section info
        sections = OrderedDict()
        for i, prov, stories in grouped:
            name = self._provider_section_name(prov, i)
            slug = _slugify(name) + f"-{i}"
            sections[slug] = {"name": name, "stories": stories, "prov": prov}

        # Build nav links
        nav_links = []
        for slug, info in sections.items():
            nav_links.append(f'<a href="#{slug}" style="text-decoration: none; color: #333; padding: 0 0.4em; font-size: 9pt;">{info["name"]}</a>')
        nav_html = ' <span style="color: #999;">\u2022</span> '.join(nav_links)

        # Collect banners (rendered above columns, full width)
        banner_html_parts = []
        # Build main and sidebar content with section anchors
        main_html_parts = []
        sidebar_html_parts = []
        game_html_parts = []

        for slug, info in sections.items():
            prov = info["prov"]
            stories = info["stories"]
            if self._is_game_provider(prov):
                anchor = f'<div id="{slug}"></div>'
                game_story_html = []
                for story in stories:
                    game_story_html.append(
                        (
                            '<div class="game-story-card" '
                            'style="page-break-inside: avoid; break-inside: avoid-page;">'
                            f"{story.to_html()}"
                            "</div>"
                        )
                    )
                if game_story_html:
                    game_html_parts.append(
                        (
                            '<div class="game-provider-section" '
                            'style="break-before: page; page-break-before: always;">'
                            f"{anchor}{'<hr />'.join(game_story_html)}"
                            "</div>"
                        )
                    )
                continue

            is_reddit = self._is_reddit_provider(prov)
            banner_stories = [s for s in stories if s.placement_preference == PlacementPreference.BANNER]
            main_stories = [s for s in stories if s.placement_preference not in [PlacementPreference.EAR, PlacementPreference.SIDEBAR, PlacementPreference.BANNER]]
            sidebar_stories = [s for s in stories if s.placement_preference == PlacementPreference.SIDEBAR]

            if banner_stories:
                anchor = f'<div id="{slug}"></div>'
                story_html = "".join(s.to_html() for s in banner_stories)
                banner_html_parts.append(f"{anchor}{story_html}")

            if main_stories:
                anchor = f'<div id="{slug}"></div>'
                wrapped_stories = []
                for story in main_stories:
                    story_html = story.to_html()
                    if is_reddit:
                        story_html = (
                            '<div class="reddit-story-card" '
                            'style="page-break-inside: avoid; break-inside: avoid-page;">'
                            f"{story_html}"
                            "</div>"
                        )
                    wrapped_stories.append(story_html)
                story_html = "<hr />".join(wrapped_stories)
                main_html_parts.append(f"{anchor}{story_html}")

            if sidebar_stories:
                anchor = f'<div id="{slug}"></div>'
                story_html = "<br />".join(s.to_html() for s in sidebar_stories)
                sidebar_html_parts.append(f"{anchor}{story_html}")

        # Keep banner content at the top of main content. Avoid
        # column-span here because WeasyPrint can push the rest of
        # the column content to the next page.
        if banner_html_parts:
            banner_block = "".join(banner_html_parts)
            banner_wrapped = f'<div class="banner-section">{banner_block}</div>'
            main_html_parts.insert(0, banner_wrapped)

        main_content = "<hr />".join(main_html_parts)
        sidebar_content = "<br />".join(sidebar_html_parts)
        games_content = "".join(game_html_parts)

        games_block = ""
        if games_content:
            games_block = (
                '<div class="games-section" '
                'style="column-count: 1; column-gap: normal;">'
                f"{games_content}"
                "</div>"
            )

        return f"""
            <html>
            <head>
                <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
                <meta charset="UTF-8" />
            </head>
            <body>
                <div class="header">
                    <div><h1>{self.title}</h1><h4>{self.subtitle}</h4></div>
                </div>
                <div class="toc-nav" style="text-align: center; padding: 0.3em 0; margin-bottom: 0.5em; border-top: 1px solid #ccc; border-bottom: 1px solid #ccc;">
                    {nav_html}
                </div>
                <div class="stories row">
                    <div class="main-stories column">
                        {main_content}
                    </div>
                    <div class="sidebar column">
                        {sidebar_content}
                    </div>
                </div>
                {games_block}
            </body>
            </html>
        """

    def to_pdf(
        self,
        filename: Union[str, io.BytesIO],
        style: Union[str] = "",
        font_size: int = 14,
    ) -> Optional[str]:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()
        style_obj = _get_style(style)
        html = self.to_html()
        h = HTML(string=html)
        base_url = str(pathlib.Path.cwd())
        c = CSS(
            string=style_obj.get_css(font_size),
            font_config=font_config,
            base_url=base_url,
        )
        if isinstance(filename, str):
            h.write_pdf(
                filename,
                stylesheets=[c, *style_obj.get_stylesheets()],
                font_config=font_config,
            )
            return filename
        elif isinstance(filename, io.BytesIO):
            tf = tempfile.NamedTemporaryFile(suffix=".pdf")
            h.write_pdf(
                tf,
                stylesheets=[c, *style_obj.get_stylesheets()],
            )
            tf.seek(0)
            filename.write(tf.read())
            return None
        else:
            raise ValueError(f"Invalid filename {filename}")

    def to_epub(
        self,
        filename: Union[str, io.BytesIO],
        style: Union[str, Type[Style]] = "",
        font_size: int = 14,
    ) -> Optional[str]:
        from ebooklib import epub

        style_obj = _get_style(style)

        stories = []
        for prov in self.story_providers:
            new_stories = prov.get_stories()
            for a in new_stories:
                if not a.headline:
                    stories.append(a)
                    continue
                for b in stories:
                    if a.headline == b.headline:
                        break
                else:
                    stories.append(a)

        book = epub.EpubBook()
        title = f"{self.title} - {self.subtitle}"
        book.set_title(title)
        book.set_language("en")

        css = epub.EpubItem(
            uid="style_default",
            file_name="style/default.css",
            media_type="text/css",
            content=style_obj.get_css(font_size),
        )
        book.add_item(css)

        chapters = []
        links = []
        no_headlines = []
        for story in stories:
            if not story.headline:
                no_headlines.append(story)
        stories = [x for x in stories if x.headline]
        for story in stories:
            file = f"{uuid4().hex}.xhtml"
            title = story.headline
            chapter = epub.EpubHtml(title=title, file_name=file, lang="en")
            links.append(file)
            chapter.content = story.to_html()
            book.add_item(chapter)
            chapters.append(chapter)

        if no_headlines:
            file = f"{uuid4().hex}.xhtml"
            chapter = epub.EpubHtml(
                title="From Reddit",
                file_name=file,
                lang="en",
            )
            links.append(file)
            chapter.content = "<br>".join([s.to_html() for s in no_headlines])
            book.add_item(chapter)
            chapters.append(chapter)

        book.toc = chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav"] + chapters

        if isinstance(filename, str):
            epub.write_epub(filename, book)
            return filename
        elif isinstance(filename, io.BytesIO):
            tf = tempfile.NamedTemporaryFile(suffix=".epub")
            epub.write_epub(tf, book)
            tf.seek(0)
            filename.write(tf.read())
            return None
