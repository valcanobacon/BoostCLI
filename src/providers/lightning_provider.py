from dataclasses import dataclass, field
from os import linesep
from typing import Any

import grpc

from src.lnd import lightning_pb2_grpc as lnrpc


def channel_from(host: str, port: str, cert: bytes, macaroon: bytes) -> grpc.Channel:
    def metadata_callback(_, callback):
        callback([("macaroon", macaroon)], None)

    cert_creds = grpc.ssl_channel_credentials(cert)
    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)

    channel = grpc.secure_channel(
        f"{host}:{port}",
        combined_creds,
        # options=[
        #     ("grpc.max_send_message_length", kwargs["max_message_length"]),
        #     ("grpc.max_receive_message_length", kwargs["max_message_length"]),
        # ],
    )

    return channel


@dataclass(frozen=True)
class lightningProvider:
    lightning_stub: lnrpc.LightningStub

    @classmethod
    def from_channel(cls, channel: grpc.Channel) -> "lightningProvider":
        return lightningProvider(
            lightning_stub=lnrpc.LightningStub(channel),
        )
