import hashlib
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict

import requests

DEFAULT_BASE_URL = "https://api.podcastindex.org/api/1.0"


@dataclass
class PodcastIndexError(Exception):
    request: requests.Request


@dataclass
class PodcastIndexResponse:
    request: requests.Request
    data: Dict


@dataclass(frozen=True)
class PodcastIndexProvider:

    api_key: str
    api_secret: str
    user_agent: str
    base_url: str = DEFAULT_BASE_URL
    requester: Any = requests.request
    timestamp: Callable[[], int] = lambda: int(time.time())

    def authorization(self, timestamp):
        return str(
            hashlib.sha1(
                f"{self.api_key}{self.api_secret}{timestamp}".encode("utf8")
            ).hexdigest()
        )

    def request(self, method: str, path: str, **kwargs) -> requests.Request:
        timestamp = self.timestamp()
        authorization = self.authorization(timestamp)
        headers = kwargs["headers"] = kwargs.setdefault("headers", {})
        headers.setdefault("User-Agent", self.user_agent)
        headers.setdefault("X-Auth-Key", self.api_key)
        headers.setdefault("X-Auth-Date", str(timestamp))
        headers.setdefault("Authorization", authorization)
        url = f"{self.base_url}{path}"
        response = self.requester(method, url, **kwargs)
        if response.status_code not in [requests.status_codes.codes.ok]:
            raise PodcastIndexError(request=response)
        data = response.json()
        if not data.get("feed"):
            raise PodcastIndexError(request=response)
        return PodcastIndexResponse(request=response, data=data)

    def podcasts_byfeedid(self, feed_id: Any) -> PodcastIndexResponse:
        return self.request("GET", f"/podcasts/byfeedid?id={feed_id}")

    def podcasts_byfeedurl(self, feed_url: Any) -> PodcastIndexResponse:
        return self.request("GET", f"/podcasts/byfeedurl?url={feed_url}")

    def podcasts_byitunesid(self, itunes_id: Any) -> PodcastIndexResponse:
        return self.request("GET", f"/podcasts/byitunesid?id={itunes_id}")

    def podcasts_byguid(self, guid: Any) -> PodcastIndexResponse:
        return self.request("GET", f"/podcasts/byguid?guid={guid}")
