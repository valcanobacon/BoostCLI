from typing import Final
from unittest.mock import ANY, Mock, sentinel

import pytest
import requests
from bs4 import BeautifulSoup

from src.providers.feed_provider import FeedError, FeedProvider, FeedResponse

FEED: Final = f"""
<rss version="2.0">
  <channel>
    <podcast:value type="lightning" method="keysend" suggested="0.00001000000">
      <podcast:valueRecipient name="Adam" type="node" address="abc" split="50"/>
      <podcast:valueRecipient name="Dave" type="node" address="cba" split="50"/>
      <podcast:valueRecipient name="Podcast Index" type="node" address="xyz" split="1" fee=true/>
    </podcast:value>
  </channel>
</rss>
"""


@pytest.fixture
def feed():
    return FEED


@pytest.fixture
def feed_soup(feed):
    return BeautifulSoup(feed, "lxml")


@pytest.fixture
def requester_mock(feed):
    mock = Mock(spec=requests.request, spec_set=True)
    mock.return_value.text = feed
    return mock


@pytest.fixture
def provider(requester_mock):
    return FeedProvider(
        requester=requester_mock,
    )


def test_request_response(requester_mock, provider, feed_soup):
    requester_mock.return_value.status_code = requests.status_codes.codes.ok
    response = provider.request(sentinel.feed_url)
    requester_mock.assert_called_once_with(
        "GET",
        sentinel.feed_url,
    )
    assert response == FeedResponse(
        request=requester_mock.return_value,
        data=feed_soup,
    )


def test_request_error(requester_mock, provider):
    requester_mock.return_value.status_code = requests.status_codes.codes.bad_request
    expected_exception = FeedError(request=requester_mock.return_value)
    with pytest.raises(FeedError) as exception:
        provider.request(
            sentinel.feed_url,
        )
        assert exception == expected_exception
    requester_mock.assert_called_once_with(
        "GET",
        sentinel.feed_url,
    )
