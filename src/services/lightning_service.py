import base64
import codecs
import hashlib
import itertools
import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generator

import grpc
from google.protobuf.json_format import MessageToJson

from src.lnd import lightning_pb2 as ln
from src.lnd import lightning_pb2_grpc as lnrpc
from src.models import BoostInvoice, ValueForValue
from src.providers.lightning_provider import lightningProvider


@dataclass(frozen=True)
class LightningService:

    provider: lightningProvider

    def parse_grpc_message(self, grpc_message) -> Any:
        return json.loads(MessageToJson(grpc_message))

    def invoices(
        self,
        index_offset=0,
        max_number_of_invoices=None,
        accending=True,
    ) -> Generator:

        request = ln.ListInvoiceRequest(
            pending_only=False,
            index_offset=index_offset,
            num_max_invoices=max_number_of_invoices,
            reversed=accending,
        )

        response = self.provider.lightning_stub.ListInvoices(request)

        invoices = self.parse_grpc_message(response)["invoices"]

        if not accending:
            invoices = reversed(invoices)

        yield from invoices

    def invoices_watch(
        self,
        index_offset=0,
        seconds_between_batches: int = 3,
    ):

        last_index_offset = index_offset

        while True:

            invoices = list(
                self.invoices(index_offset=last_index_offset, accending=True)
            )

            if not invoices:
                time.sleep(seconds_between_batches)
                continue

            yield from invoices

            last_index_offset += len(invoices)

            time.sleep(seconds_between_batches)

    def watch_value_received(
        self,
        index_offset=0,
        seconds_between_batches: int = 3,
    ):
        last_index_offset = index_offset

        while True:

            values = list(
                self.value_received(index_offset=last_index_offset, accending=True)
            )

            if not values:
                time.sleep(seconds_between_batches)
                continue

            yield from values

            last_index_offset += len(values)

            time.sleep(seconds_between_batches)

    def value_received(
        self,
        index_offset=0,
        max_number_of_invoices=None,
        accending=True,
    ) -> Generator:

        request = ln.ListInvoiceRequest(
            pending_only=False,
            index_offset=index_offset,
            num_max_invoices=max_number_of_invoices,
            reversed=accending,
        )

        response = self.provider.lightning_stub.ListInvoices(request)

        invoices = self.parse_grpc_message(response)["invoices"]

        if not accending:
            invoices = reversed(invoices)

        for invoice in invoices:
            if invoice["state"] != "SETTLED":
                continue

            tlv = invoice["htlcs"][0]
            custom_records = parse_custom_records(tlv.get("customRecords", {}))

            if "podcastindex_records_v2" in custom_records:
                record = custom_records["posdcastindex_records_v2"]

            elif "podcastindex_records_v1" in custom_records:
                record = custom_records["podcastindex_records_v1"]

                timestamp = None
                try:
                    if "ts" in record:
                        timestamp = int(record["ts"])
                    elif "time" in record:
                        struct_time = time.strptime(record["time"], "%H:%M:%S")
                        timestamp = (
                            struct_time.tm_hour * 60 * 60
                            + struct_time.tm_min * 60
                            + struct_time.tm_sec
                        )
                except TypeError:
                    pass

                amount_msats_total = None
                if "value_msat_total" in record:
                    amount_msats_total = int(record["value_msat_total"])

                yield ValueForValue(
                    creation_date=datetime.fromtimestamp(int(invoice["creationDate"])),
                    amount_msats=int(invoice["valueMsat"]),
                    amount_msats_total=amount_msats_total,
                    boost=record.get("action") == "boost",
                    sender_name=record.get("sender_name"),
                    sender_id=record.get("sender_id"),
                    sender_key=record.get("sender_key"),
                    sender_app_name=record.get("app_name"),
                    sender_app_version=record.get("app_version"),
                    receiver_name=record.get("name"),
                    message=record.get("message"),
                    podcast_title=record.get("podcast"),
                    podcast_url=record.get("url"),
                    podcast_guid=record.get("guid"),
                    episode_title=record.get("episode"),
                    episode_guid=record.get("episode_guid"),
                    podcast_index_feed_id=record.get("feedID"),
                    podcast_index_item_id=record.get("itemID"),
                    timestamp=timestamp,
                )

    def pay_boost_invoice(self, invoice: BoostInvoice):
        def value_to_record(value: ValueForValue):
            value = {
                "action": "boost" if value.boost else None,
                "sender_name": value.sender_name,
                "sender_id": value.sender_id,
                "sender_key": value.sender_key,
                "app_name": value.sender_app_name,
                "app_value": value.sender_app_version,
                "name": value.receiver_name,
                "message": value.message,
                "podcast": value.podcast_title,
                "url": value.podcast_url,
                "episode": value.episode_title,
                "episode_guid": value.episode_guid,
                "feedID": value.podcast_index_feed_id,
                "itemID": value.podcast_index_item_id,
                "ts": value.timestamp,
            }

            value = json.dumps({k: v for k, v in value.items() if v is not None})
            value = value.encode("utf8")
            value = base64.b64encode(value)
            return value

        def request_generator(invoice: BoostInvoice):
            for destination in itertools.chain(invoice.payments, invoice.fees):
                secret = secrets.token_bytes(32)
                hashed_secret = hashlib.sha256(secret).hexdigest()
                custom_records = [
                    (5482373484, secret),
                    (7629169, value_to_record(destination)),
                ]
                dest = codecs.decode(destination.receiver_address, "hex")
                request = ln.SendRequest(
                    dest=dest,
                    amt_msat=destination.amount_msats,
                    dest_custom_records=custom_records,
                    payment_hash=bytes.fromhex(hashed_secret),
                    allow_self_payment=True,
                )
                yield request

        request_iterable = request_generator(invoice)
        for payment in self.provider.lightning_stub.SendPayment(request_iterable):
            yield payment


def try_to_json_decode(value: str) -> Any:
    try:
        return json.loads(value)
    except json.decoder.JSONDecodeError:
        return None


def parse_custom_records(custom_records):
    parsed = {}

    for key, value in custom_records.items():
        if key in ("7629169", "133773310"):
            value = base64.b64decode(value).decode("utf8")
            value = try_to_json_decode(value)
        elif key in ("34349334", "34349340", "34349343", "34349345", "34349347"):
            value = base64.b64decode(value).decode("utf8")

        parsed[key] = value

    whatsat_records = dict(
        message=parsed.get("34349334"),
        signature=parsed.get("34349337"),
        sender_pubkey=parsed.get("34349339"),
        timestamp=parsed.get("34349343"),
    )
    whatsat_records = dict(
        filter(lambda item: item[1] is not None, whatsat_records.items())
    )
    if not whatsat_records:
        whatsat_records = None

    records = dict(
        keysend_preimage=parsed.get("5482373484"),
        podcastindex_records_v1=parsed.get("7629169"),
        podcastindex_records_v2=parsed.get("7629173"),  # WIP
        podcastindex_id=parsed.get("7629175"),
        whatsat_records=whatsat_records,
        sphinx_records=parsed.get("133773310"),
    )

    return dict(filter(lambda item: item[1] is not None, records.items()))
