import requests
from typing import List

from goosepaper.storyprovider.storyprovider import StoryProvider
from goosepaper.story import Story
from goosepaper.util import PlacementPreference


class NasaApodStoryProvider(StoryProvider):
    def __init__(self, api_key: str = "DEMO_KEY"):
        self.api_key = api_key

    def get_stories(self, limit: int = 1, **kwargs) -> List[Story]:
        stories = []
        try:
            resp = requests.get(
                f"https://api.nasa.gov/planetary/apod?api_key={self.api_key}",
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            title = data.get("title", "Astronomy Picture of the Day")
            explanation = data.get("explanation", "")
            media_type = data.get("media_type", "image")
            url = data.get("url", "")

            if media_type == "image":
                body_html = f"""
                <div style="text-align: center;">
                    <img src="{url}" style="max-width: 100%;" />
                </div>
                <p>{explanation}</p>
                """
            else:
                body_html = f"<p>{explanation}</p><p>(Today's APOD is a video: {url})</p>"

            stories.append(
                Story(
                    headline=f"NASA: {title}",
                    body_html=body_html,
                    byline="NASA Astronomy Picture of the Day",
                )
            )
        except Exception as e:
            print(f"NASA APOD provider error: {e}")

        return stories
