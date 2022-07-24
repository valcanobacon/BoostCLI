import codecs
import hashlib
import itertools
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generator, Optional

import grpc
from google.protobuf.json_format import MessageToJson
from lndgrpc import LNDClient

from src.models import BoostInvoice, ValueForValue


def client_from(
    host: str, port: str, cert_filepath: str, macaroon_filepath: str
) -> grpc.Channel:
    return LNDClient(
        ip_address=f"{host}:{port}",
        cert_filepath=cert_filepath,
        macaroon_filepath=macaroon_filepath,
    )


@dataclass(frozen=True)
class LightningService:

    client: LNDClient

    @classmethod
    def from_client(cls, client: LNDClient) -> "LightningService":
        return LightningService(client=client)

    def parse_grpc_message(self, grpc_message) -> Any:
        return json.loads(MessageToJson(grpc_message))

    def get_info(self):
        return self.client.get_info()

    def invoices(
        self,
        index_offset=0,
        max_number_of_invoices=None,
        accending=True,
        pending_only=False,
    ) -> Generator:

        response = self.client.list_invoices(
            index_offset=index_offset,
            num_max_invoices=max_number_of_invoices,
            reversed=accending,
            pending_only=pending_only,
        )

        if not response:
            return

        invoices = response.invoices

        if not accending:
            invoices = reversed(invoices)

        yield from invoices

    def watch_value_received(self):
        for invoice in self.client.subscribe_invoices():
            try:
                value = self.invoice_to_value(invoice)
            except:
                continue
            if value is not None:
                yield value

    def value_received(
        self,
        index_offset=0,
        max_number_of_invoices=None,
        accending=True,
    ) -> Generator:

        invoices = self.invoices(
            index_offset=index_offset,
            max_number_of_invoices=max_number_of_invoices,
            accending=accending,
            pending_only=False,
        )

        for invoice in invoices:
            value = self.invoice_to_value(invoice)
            if value is not None:
                yield value

    def invoice_to_value(self, invoice) -> Optional[ValueForValue]:
        if not invoice.settled:
            return

        tlv = invoice.htlcs[0]
        custom_records = parse_custom_records(tlv.custom_records)

        if "podcastindex_records_v2" in custom_records:
            record = custom_records["posdcastinpex_records_v2"]

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

            return ValueForValue(
                creation_date=datetime.fromtimestamp(int(invoice.creation_date)),
                amount_msats=int(invoice.value_msat),
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
                "app_name": value.sender_app_name,
                "sender_name": value.sender_name,
                "sender_id": value.sender_id,
                "sender_key": value.sender_key,
                "app_version": value.sender_app_version,
                "name": value.receiver_name,
                "message": value.message,
                "podcast": value.podcast_title,
                "guid": value.podcast_guid,
                "url": value.podcast_url,
                "episode": value.episode_title,
                "episode_guid": value.episode_guid,
                "feedID": value.podcast_index_feed_id,
                "itemID": value.podcast_index_item_id,
                "ts": value.timestamp,
                "value_msat_total": value.amount_msats_total,
            }
            value = json.dumps({k: v for k, v in value.items() if v is not None})
            value = value.encode("utf8")
            return value

        for destination in itertools.chain(invoice.payments, invoice.fees):
            secret = secrets.token_bytes(32)
            hashed_secret = hashlib.sha256(secret).hexdigest()
            custom_records = [
                (5482373484, secret),
                (7629169, value_to_record(destination)),
            ]
            if destination.custom_key and destination.custom_value:
                custom_records.append(
                    (destination.custom_key, destination.custom_value)
                )

            dest = codecs.decode(destination.receiver_address, "hex")

            response = self.client.send_payment(
                payment_request=None,
                fee_limit_msat=int(destination.amount_msats * 0.10),
                dest=dest,
                amt_msat=destination.amount_msats,
                dest_custom_records=custom_records,
                payment_hash=bytes.fromhex(hashed_secret),
                allow_self_payment=True,
            )
            if not response:
                continue
            yield response


def try_to_json_decode(value: str) -> Any:
    try:
        return json.loads(value)
    except json.decoder.JSONDecodeError:
        return None


def parse_custom_records(custom_records):
    parsed = {}

    for key, value in custom_records.items():
        if key in (7629169, 133773310):
            try:
                parsed[key] = json.loads(value.decode("utf8"))
            except json.decoder.JSONDecodeError:
                pass

    whatsat_records = dict(
        message=parsed.get(34349334),
        signature=parsed.get(34349337),
        sender_pubkey=parsed.get(34349339),
        timestamp=parsed.get(34349343),
    )
    whatsat_records = dict(
        filter(lambda item: item[1] is not None, whatsat_records.items())
    )
    if not whatsat_records:
        whatsat_records = None

    records = dict(
        keysend_preimage=parsed.get(5482373484),
        podcastindex_records_v1=parsed.get(7629169),
        podcastindex_records_v2=parsed.get(7629173),  # WIP
        podcastindex_id=parsed.get(7629175),
        whatsat_records=whatsat_records,
        sphinx_records=parsed.get(133773310),
    )

    return dict(filter(lambda item: item[1] is not None, records.items()))
