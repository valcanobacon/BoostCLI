from dataclasses import dataclass
from unittest.mock import Mock, sentinel

import grpc
import pytest

from src.lnd import lightning_pb2_grpc as lnrpc
from src.providers.lightning_provider import lightningProvider


@pytest.fixture
def channel_mock():
    return Mock(spec=grpc.Channel, set_spec=True)


@pytest.fixture
def lightning_stub_mock():
    return Mock(spec=lnrpc.LightningStub, set_spec=True)


@pytest.fixture
def provider(lightning_stub_mock):
    return lightningProvider(
        lightning_stub=lightning_stub_mock,
    )


def test_provider(provider, lightning_stub_mock):
    assert provider.lightning_stub is lightning_stub_mock
