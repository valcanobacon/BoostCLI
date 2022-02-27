from dataclasses import dataclass
from typing import Callable

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class FeedError(Exception):
    request: requests.Request


@dataclass(frozen=True)
class FeedResponse:
    request: requests.Request
    data: BeautifulSoup


@dataclass(frozen=True)
class FeedProvider:

    requester: Callable = requests.request

    def request(self, feed_url, method="GET"):
        response = self.requester(method, feed_url)
        if response.status_code not in [requests.status_codes.codes.ok]:
            raise FeedError(request=response)
        soup = BeautifulSoup(response.text, "lxml")
        return FeedResponse(request=response, data=soup)
