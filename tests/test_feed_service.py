from unittest.mock import Mock, sentinel

import pytest
from bs4 import BeautifulSoup

from src.models import PodcastValue, PodcastValueDestination
from src.providers.feed_provider import FeedError, FeedProvider, FeedResponse
from src.services.feed_service import FeedService

FEED = """
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

FEED_WITH_LIVE_VALUE = """
<rss version="2.0">
  <channel>
    <podcast:value type="lightning" method="keysend" suggested="0.00001000000">
      <podcast:valueRecipient name="Adam" type="node" address="abc" split="50"/>
      <podcast:valueRecipient name="Dave" type="node" address="cba" split="50"/>
      <podcast:valueRecipient name="Podcast Index" type="node" address="xyz" split="1" fee=true/>
    </podcast:value>
    <podcast:liveitem status="pending">
        <podcast:value type="lightning" method="keysend" suggested="0.00001000000">
            <podcast:valueRecipient name="Adam" type="node" address="abc" split="33"/>
            <podcast:valueRecipient name="Dave" type="node" address="cba" split="33"/>
            <podcast:valueRecipient name="GuestA" type="node" address="cba" split="33"/>
            <podcast:valueRecipient name="Podcast Index" type="node" address="xyz" split="1" fee=true/>
        </podcast:value>
    </podcast:liveitem>
    <podcast:liveitem status="live">
        <title>Live!</title>
        <guid>123</guid>
        <podcast:value type="lightning" method="keysend" suggested="0.00001000000">
            <podcast:valueRecipient name="Adam" type="node" address="abc" split="33"/>
            <podcast:valueRecipient name="Dave" type="node" address="cba" split="33"/>
            <podcast:valueRecipient name="GuestB" type="node" address="cba" split="33"/>
            <podcast:valueRecipient name="Podcast Index" type="node" address="xyz" split="1" fee=true/>
        </podcast:value>
    </podcast:liveitem>
  </channel>
</rss>
"""


@pytest.fixture
def feed():
    return BeautifulSoup(FEED, "lxml")


@pytest.fixture
def feed_with_live_value():
    return BeautifulSoup(FEED_WITH_LIVE_VALUE, "lxml")


@pytest.fixture
def podcast_value():
    return PodcastValue(
        suggested="0.00001000000",
        podcast_url=sentinel.feed_url,
        destinations=[
            PodcastValueDestination(
                name="Adam",
                address="abc",
                split=50,
                fee=False,
            ),
            PodcastValueDestination(
                name="Dave",
                address="cba",
                split=50,
                fee=False,
            ),
            PodcastValueDestination(
                name="Podcast Index",
                address="xyz",
                split=1,
                fee=True,
            ),
        ],
    )


@pytest.fixture
def podcast_value_with_live_value():
    return PodcastValue(
        suggested="0.00001000000",
        podcast_url=sentinel.feed_url,
        podcast_title="Live!",
        episode_title="Live!",
        episode_guid="123",
        destinations=[
            PodcastValueDestination(
                name="Adam",
                address="abc",
                split=33,
                fee=False,
            ),
            PodcastValueDestination(
                name="Dave",
                address="cba",
                split=33,
                fee=False,
            ),
            PodcastValueDestination(
                name="GuestB",
                address="cba",
                split=33,
                fee=False,
            ),
            PodcastValueDestination(
                name="Podcast Index",
                address="xyz",
                split=1,
                fee=True,
            ),
        ],
    )


@pytest.fixture
def provider_mock(feed):
    return Mock(spec=FeedProvider, set_spec=True)


@pytest.fixture
def service(provider_mock):
    return FeedService(
        provider=provider_mock,
    )


@pytest.fixture
def podcast_value_response(provider_mock, feed):
    return FeedResponse(
        request=provider_mock.return_value,
        data=feed,
    )


@pytest.fixture
def podcast_value_with_live_value_response(provider_mock, feed_with_live_value):
    return FeedResponse(
        request=provider_mock.return_value,
        data=feed_with_live_value,
    )


@pytest.fixture
def feed_error(provider_mock):
    return FeedError(
        request=provider_mock.return_value,
    )


def test_podcast_value(service, provider_mock, podcast_value, podcast_value_response):
    provider_mock.request.return_value = podcast_value_response
    response = service.podcast_value(sentinel.feed_url)
    assert response == podcast_value


def test_podcast_value_with_live(
    service,
    provider_mock,
    podcast_value_with_live_value,
    podcast_value_with_live_value_response,
):
    provider_mock.request.return_value = podcast_value_with_live_value_response
    response = service.podcast_value(sentinel.feed_url)
    assert response == podcast_value_with_live_value
