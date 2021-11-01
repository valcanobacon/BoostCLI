from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4


@dataclass
class PodcastValueDestination:
    split: int
    address: str
    name: Optional[str] = None
    fee: bool = False


@dataclass
class PodcastValue:
    destinations: List[PodcastValueDestination]
    suggested: Optional[str] = None
    podcast_url: Optional[str] = None
    podcast_title: Optional[str] = None
    podcast_guid: Optional[str] = None
    podcast_index_feed_id: Optional[int] = None
    podcast_index_item_id: Optional[int] = None


@dataclass
class ValueForValue:
    amount_msats: int
    boost: bool = True
    creation_date: Optional[datetime] = None
    uuid: Optional[UUID] = None
    receiver_name: Optional[str] = None
    receiver_address: Optional[str] = None
    amount_msats_total: Optional[int] = None
    message: Optional[str] = None
    podcast_index_feed_id: Optional[str] = None
    podcast_index_item_id: Optional[str] = None
    podcast_url: Optional[str] = None
    podcast_title: Optional[str] = None
    podcast_guid: Optional[str] = None
    episode_title: Optional[str] = None
    episode_guid: Optional[str] = None
    sender_key: Optional[str] = None
    sender_name: Optional[str] = None
    sender_id: Optional[str] = None
    sender_app_name: Optional[str] = None
    sender_app_version: Optional[str] = None
    timestamp: Optional[int] = None


@dataclass
class BoostInvoice:
    amount: int
    podcast_value: PodcastValue
    fees: List[ValueForValue] = field(init=False, default_factory=lambda: [])
    payments: List[ValueForValue] = field(init=False, default_factory=lambda: [])
    amount_fees: int = field(init=False, default=0)
    amount_after_fees: int = field(init=False)

    @classmethod
    def create(
        cls, podcast_value: PodcastValue, amount: int, message: str, sender_name: str
    ) -> "BoostInvoice":

        invoice = BoostInvoice(
            amount=amount,
            podcast_value=podcast_value,
        )

        for destination in invoice.podcast_value.destinations:
            if not destination.fee:
                continue
            amount_msats = int(destination.split * (invoice.amount * 0.01))
            invoice.amount_fees += amount_msats
            invoice.fees.append(
                ValueForValue(
                    receiver_address=destination.address,
                    amount_msats=amount_msats,
                    boost=True,
                    amount_msats_total=invoice.amount,
                    podcast_title=invoice.podcast_value.podcast_title,
                    podcast_url=invoice.podcast_value.podcast_url,
                    podcast_index_item_id=invoice.podcast_value.podcast_index_item_id,
                    podcast_guid=invoice.podcast_value.podcast_guid,
                    receiver_name=destination.name,
                )
            )

        invoice.amount_after_fees = int(invoice.amount - invoice.amount_fees)

        amount_remaining = invoice.amount_after_fees

        for destination in invoice.podcast_value.destinations:
            if destination.fee:
                continue

            amount_msats = min(
                int(destination.split * (invoice.amount_after_fees * 0.01)),
                amount_remaining,
            )
            amount_remaining -= amount_msats
            invoice.payments.append(
                ValueForValue(
                    receiver_address=destination.address,
                    amount_msats=amount_msats,
                    boost=True,
                    amount_msats_total=invoice.amount,
                    message=message,
                    podcast_title=invoice.podcast_value.podcast_title,
                    podcast_url=invoice.podcast_value.podcast_url,
                    podcast_index_item_id=invoice.podcast_value.podcast_index_item_id,
                    podcast_guid=invoice.podcast_value.podcast_guid,
                    receiver_name=destination.name,
                    sender_name=sender_name,
                )
            )

        return invoice
