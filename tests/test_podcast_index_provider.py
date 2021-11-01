from unittest.mock import ANY, Mock, sentinel

import pytest
import requests

from src.providers.podcast_index_provider import (
    PodcastIndexError,
    PodcastIndexProvider,
    PodcastIndexResponse,
)


@pytest.fixture
def requester_mock():
    return Mock(spec=requests.request, spec_set=True)


@pytest.fixture
def timestamp_mock():
    return Mock()


@pytest.fixture
def api_key():
    return "x" * 21


@pytest.fixture
def api_secret():
    return "x" * 41


@pytest.fixture
def user_agent():
    return "boostaccount"


@pytest.fixture
def provider(api_key, api_secret, user_agent, requester_mock, timestamp_mock):
    return PodcastIndexProvider(
        api_key=api_key,
        api_secret=api_secret,
        user_agent=user_agent,
        requester=requester_mock,
        timestamp=timestamp_mock,
    )


def test_request_response(requester_mock, timestamp_mock, provider):
    requester_mock.return_value.status_code = requests.status_codes.codes.ok
    respones = provider.request(
        sentinel.method,
        sentinel.path,
    )
    requester_mock.assert_called_once_with(
        sentinel.method,
        f"{provider.base_url}{sentinel.path}",
        headers={
            "User-Agent": provider.user_agent,
            "X-Auth-Key": provider.api_key,
            "X-Auth-Date": str(timestamp_mock.return_value),
            "Authorization": provider.authorization(timestamp_mock.return_value),
        },
    )
    assert respones == PodcastIndexResponse(
        request=requester_mock.return_value,
        data=requester_mock.return_value.json.return_value,
    )


def test_request_error(requester_mock, timestamp_mock, provider):
    requester_mock.return_value.status_code = requests.status_codes.codes.bad_request
    expected_exception = PodcastIndexError(request=requester_mock.return_value)
    with pytest.raises(PodcastIndexError) as exception:
        provider.request(
            sentinel.method,
            sentinel.path,
        )
        assert exception == expected_exception
    requester_mock.assert_called_once_with(
        sentinel.method,
        f"{provider.base_url}{sentinel.path}",
        headers={
            "User-Agent": provider.user_agent,
            "X-Auth-Key": provider.api_key,
            "X-Auth-Date": str(timestamp_mock.return_value),
            "Authorization": provider.authorization(timestamp_mock.return_value),
        },
    )
