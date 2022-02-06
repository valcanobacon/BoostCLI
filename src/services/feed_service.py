from dataclasses import dataclass
from typing import Optional

from bs4.element import Tag

from src.providers.feed_provider import FeedProvider

from ..models import PodcastValue, PodcastValueDestination


@dataclass(frozen=True)
class FeedService:

    provider: FeedProvider = FeedProvider()

    def podcast_value(self, feed_url) -> Optional[PodcastValue]:
        try:
            response = self.provider.request(feed_url)
        except:
            return

        podcast_guid = None
        soup = response.data.find("podcast:guid")
        if soup is not None:
            podcast_guid = soup.text

        podcast_title = None
        soup = response.data.find("title")
        if soup is not None:
            podcast_title = soup.text

        podcast_value_soup = next(
            iter(response.data.find_all("podcast:value", recursive=True, limit=True)),
            None,
        )
        if podcast_value_soup is None:
            return

        try:
            if podcast_value_soup["type"] not in ["lightning"]:
                return
            if podcast_value_soup["method"] not in ["keysend"]:
                return
            suggested = podcast_value_soup.get("suggested")
        except KeyError:
            return

        podcast_value = PodcastValue(
            podcast_url=feed_url,
            podcast_title=podcast_title,
            podcast_guid=podcast_guid,
            suggested=suggested,
            destinations=[],
        )

        try:
            for destination in podcast_value_soup.children:
                if not isinstance(destination, Tag):
                    continue
                if destination["type"] not in ["node"]:
                    continue
                custom_key = destination.get("customkey")
                if custom_key is not None:
                    custom_key = int(custom_key)
                custom_value = destination.get("customvalue")
                if custom_value:
                    custom_value = custom_value.encode("utf8")
                podcast_value.destinations.append(
                    PodcastValueDestination(
                        address=destination["address"],
                        split=int(destination["split"]),
                        fee=bool(destination.get("fee", False)),
                        name=destination.get("name"),
                        custom_key=custom_key,
                        custom_value=custom_value,
                    )
                )
        except (KeyError, ValueError):
            pass

        return podcast_value
