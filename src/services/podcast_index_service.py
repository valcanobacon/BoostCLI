from dataclasses import dataclass
from typing import Optional

from ..models import PodcastValue, PodcastValueDestination
from ..providers.podcast_index_provider import PodcastIndexError, PodcastIndexProvider


@dataclass(frozen=True)
class PodcastIndexService:

    provider: PodcastIndexProvider

    def get_podcast(self, id_key):

        try:
            print("Searching by Feed URL")
            response = self.provider.podcasts_byfeedurl(id_key)
        except PodcastIndexError:
            pass
        else:
            return response

        try:
            print("Searching by Feed ID")
            response = self.provider.podcasts_byfeedid(id_key)
        except PodcastIndexError:
            pass
        else:
            return response

        try:
            print("Searching by GUID")
            response = self.provider.podcasts_byguid(id_key)
        except PodcastIndexError:
            pass
        else:
            return response

        try:
            print("Searching by Itunes ID")
            response = self.provider.podcasts_byitunesid(id_key)
        except PodcastIndexError:
            pass
        else:
            return response

    def podcast_value(self, feed_url) -> Optional[PodcastValue]:

        response = self.get_podcast(feed_url)
        if response is None:
            return

        data = response.data

        try:
            model = data["feed"]["value"]["model"]
            if model["type"] not in ["lightning"]:
                return
            if model["method"] not in ["keysend"]:
                return
            suggested = model.get("suggested")
            podcast_title = data["feed"].get("title")
            podcast_guid = data["feed"].get("podcastGuid")
            podcast_index_feed_id = data["feed"].get("id")
        except (KeyError, TypeError):
            return

        podcast_value = PodcastValue(
            podcast_title=podcast_title,
            podcast_url=feed_url,
            podcast_guid=podcast_guid,
            podcast_index_feed_id=podcast_index_feed_id,
            suggested=suggested,
            destinations=[],
        )

        try:
            for destination in data["feed"]["value"]["destinations"]:
                if destination["type"] not in ["node"]:
                    continue
                custom_key = destination.get("customKey")
                if custom_key is not None:
                    custom_key = int(custom_key)
                custom_value = destination.get("customValue")
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
