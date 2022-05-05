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
        if soup:
            podcast_guid = soup.text

        podcast_title = None
        soup = response.data.find("title", recursive=True)
        if soup:
            podcast_title = soup.text

        podcast_desc = None
        soup = response.data.find("description", recursive=False)
        if soup:
            podcast_desc = soup.text

        podcast_value_soup = None
        podcast_liveitem_soup = None

        podcast_liveitems = response.data.find_all(
            "podcast:liveitem",
            recursive=True,
            attrs={"status": "live"}
            # "podcast:liveitem", recursive=True,
        )
        for soup in podcast_liveitems:
            podcast_liveitem_soup = soup
            podcast_value_soup = next(
                iter(soup.find_all("podcast:value")),
                None,
            )
            if podcast_value_soup:
                break

        if not podcast_value_soup:
            podcast_liveitem_soup = None
            podcast_value_soup = next(
                iter(response.data.find_all("podcast:value", recursive=True)),
                None,
            )

        if not podcast_value_soup:
            return

        try:
            if podcast_value_soup["type"] not in ["lightning"]:
                return
            if podcast_value_soup["method"] not in ["keysend"]:
                return
            suggested = podcast_value_soup.get("suggested")
        except KeyError:
            return

        episode_title = None
        episode_guid = None

        if podcast_liveitem_soup:
            soup = podcast_liveitem_soup.find("title")
            if soup:
                episode_title = soup.text

            soup = podcast_liveitem_soup.find("guid")
            if soup:
                episode_guid = soup.text

        podcast_value = PodcastValue(
            podcast_url=feed_url,
            podcast_title=podcast_title,
            podcast_desc=podcast_desc,
            podcast_guid=podcast_guid,
            episode_title=episode_title,
            episode_guid=episode_guid,
            suggested=suggested,
            destinations=[],
        )

        try:
            for destination in podcast_value_soup.children:
                if not isinstance(destination, Tag):
                    continue
                if destination.get("type", "node") not in ["node"]:
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

        if not podcast_value.destinations:
            return

        return podcast_value
