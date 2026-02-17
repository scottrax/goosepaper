import requests
from typing import List

from goosepaper.storyprovider.storyprovider import StoryProvider
from goosepaper.story import Story
from goosepaper.util import PlacementPreference


class XKCDStoryProvider(StoryProvider):
    def __init__(self, num_comics: int = 1):
        self.num_comics = num_comics

    def get_stories(self, limit: int = 1, **kwargs) -> List[Story]:
        stories = []
        try:
            resp = requests.get("https://xkcd.com/info.0.json", timeout=10)
            resp.raise_for_status()
            data = resp.json()

            title = data.get("safe_title", data.get("title", "XKCD"))
            img_url = data.get("img", "")
            alt = data.get("alt", "")

            body_html = f"""
            <div style="text-align: center;">
                <img src="{img_url}" style="max-width: 100%;" />
                <p style="font-style: italic; font-size: 10pt; margin-top: 0.5em;">{alt}</p>
            </div>
            """

            stories.append(
                Story(
                    headline=f"XKCD: {title}",
                    body_html=body_html,
                    byline="xkcd.com",
                )
            )
        except Exception as e:
            print(f"XKCD provider error: {e}")

        return stories
