from unittest.mock import Mock, sentinel

import pytest

from src.models import PodcastValue, PodcastValueDestination
from src.providers.podcast_index_provider import PodcastIndexProvider
from src.services.podcast_index_service import PodcastIndexService


@pytest.fixture
def provider_mock():
    return Mock(spec=PodcastIndexProvider, set_spec=True)


@pytest.fixture
def service(provider_mock):
    return PodcastIndexService(provider_mock)


@pytest.fixture
def empty_feed():
    return {}


@pytest.fixture
def feed():
    return {
        "feed": {
            "value": {
                "model": {
                    "type": "lightning",
                    "method": "keysend",
                    "suggested": "0.00001000",
                },
                "destinations": [
                    {
                        "name": "Adam",
                        "address": "abc",
                        "split": 50,
                        "type": "node",
                        "fee": False,
                    },
                    {
                        "name": "Dave",
                        "address": "abc",
                        "split": 50,
                        "type": "node",
                    },
                    {
                        "name": "Podcast Index",
                        "address": "abc",
                        "split": 1,
                        "type": "node",
                        "fee": True,
                    },
                ],
            }
        }
    }


@pytest.fixture
def podcast_value():
    return PodcastValue(
        suggested="0.00001000",
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
                address="abc",
                split=50,
                fee=False,
            ),
            PodcastValueDestination(
                name="Podcast Index",
                address="abc",
                split=1,
                fee=True,
            ),
        ],
    )


def test_empty_feed(provider_mock, service, empty_feed):
    provider_mock.podcasts_byfeedurl.return_value.data = empty_feed
    response = service.podcast_value(feed_url=sentinel.feed_url)
    assert response is None


def test_feed(provider_mock, service, feed, podcast_value):
    provider_mock.podcasts_byfeedurl.return_value.data = feed
    response = service.podcast_value(feed_url=sentinel.feed_url)
    assert response == podcast_value


def test_feed_not_lightning(provider_mock, service, feed):
    feed["feed"]["value"]["model"]["type"] = "hive"
    provider_mock.podcasts_byfeedurl.return_value.data = feed
    response = service.podcast_value(feed_url=sentinel.feed_url)
    assert response is None


def test_feed_not_keysend(provider_mock, service, feed):
    feed["feed"]["value"]["model"]["method"] = "invoice"
    provider_mock.podcasts_byfeedurl.return_value.data = feed
    response = service.podcast_value(feed_url=sentinel.feed_url)
    assert response is None


def test_feed_not_destination_node(provider_mock, service, feed, podcast_value):
    feed["feed"]["value"]["destinations"][0]["type"] = "A"
    podcast_value.destinations.pop(0)
    provider_mock.podcasts_byfeedurl.return_value.data = feed
    response = service.podcast_value(feed_url=sentinel.feed_url)
    assert response == podcast_value
