import base64
import codecs
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from re import T
from typing import Any, List, Optional

import click
from google.protobuf.json_format import MessageToJson
from tabulate import tabulate

from src.models import BoostInvoice, ValueForValue
from src.services.feed_service import FeedService

from ..lnd import lightning_pb2 as ln
from ..lnd import lightning_pb2_grpc as lnrpc
from ..providers.lightning_provider import channel_from, lightningProvider
from ..providers.podcast_index_provider import PodcastIndexProvider
from ..services.lightning_service import LightningService
from ..services.podcast_index_service import PodcastIndexService


@click.group()
@click.option("--address", default="127.0.0.1")
@click.option("--port", type=click.IntRange(0), default=10009)
@click.option("--macaroon", type=click.Path(exists=True), default="readonly.macaroon")
@click.option("--tlscert", type=click.Path(exists=True), default="tls.cert")
@click.option("--max-message-length", type=click.IntRange(0), default=7777777)
@click.pass_context
def cli(ctx, **kwargs):
    ctx.ensure_object(dict)

    # from: https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md
    # Due to updated ECDSA generated tls.cert we need to let gprc know that
    # we need to use that cipher suite otherwise there will be a handhsake
    # error when we communicate with the lnd rpc server.
    os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"

    ctx.obj["lightning_service"] = LightningService(
        provider=lightningProvider.from_channel(
            channel_from(
                host=kwargs["address"],
                port=kwargs["port"],
                cert=read_tlscert(filename=kwargs["tlscert"]),
                macaroon=read_macaroon(filename=kwargs["macaroon"]),
            )
        )
    )

    ctx.obj["podcast_index_service"] = PodcastIndexService(
        provider=PodcastIndexProvider(
            user_agent="Boost Account",
            api_key="5K3YPBAKHWAEBR6R9ZNY",
            api_secret="zrnd^d9HtMH4aH#vBQSPsSKES6$pVtv^ra2dkQFq",
        )
    )

    ctx.obj["feed_service"] = FeedService()


@cli.command()
@click.option("--datetime-range-end", type=click.DateTime())
@click.option("--accending/--decending", default=False)
@click.option("--show-chats/--no-show-chats", default=True)
@click.option("--show-boots/--no-show-boots", default=True)
@click.option("--show-streamed/--no-show-streamed", default=True)
@click.option("--show-sphinx/--no-show-sphinx", default=True)
@click.option("--show-other/--no-show-other", default=False)
@click.option("--max-number-of-invoices", type=click.IntRange(0), default=10000)
@click.option("--index-offset", type=click.IntRange(0), default=0)
@click.pass_context
def boosts_received_list(ctx, **kwargs):
    lighting_service: LightningService = ctx.obj["lightning_service"]

    value_received = lighting_service.value_received(
        index_offset=kwargs["index_offset"],
        accending=kwargs["accending"],
        max_number_of_invoices=kwargs["max_number_of_invoices"],
    )

    for value in value_received:
        print_value(value)


@cli.command()
@click.option("--datetime-range-end", type=click.DateTime())
@click.option("--show-chats/--no-show-chats", default=True)
@click.option("--show-boots/--no-show-boots", default=True)
@click.option("--show-streamed/--no-show-streamed", default=True)
@click.option("--show-sphinx/--no-show-sphinx", default=True)
@click.option("--show-other/--no-show-other", default=False)
@click.option("--max-number-of-invoices", type=click.IntRange(0), default=100)
@click.option("--index-offset", type=click.IntRange(0), default=0)
@click.option("--sleep-time", type=click.IntRange(1), default=1)
@click.pass_context
def boosts_received_watch(ctx, **kwargs):
    lighting_service: LightningService = ctx.obj["lightning_service"]

    for invoice in lighting_service.watch_value_received(
        index_offset=kwargs["index_offset"],
    ):
        print_value(invoice)


@cli.command()
@click.pass_context
@click.argument("feed-url")
def podcast(ctx, feed_url):
    feed_service: FeedService = ctx.obj["feed_service"]
    podcast_index_service: Optional[PodcastIndexService] = ctx.obj.get(
        "podcast_index_service"
    )

    podcast_value = feed_service.podcast_value(feed_url)

    if podcast_value is None and podcast_index_service is not None:
        # Get from Podcast index
        podcast_value = podcast_index_service.podcast_value(feed_url)
        if podcast_value is None:
            pass

    if podcast_value is None:
        click.echo("No Value Block")
        exit(1)

    click.echo(
        tabulate(
            [
                ["Title", podcast_value.podcast_title],
                ["URL", podcast_value.podcast_url],
                ["GUID", podcast_value.podcast_guid],
                ["Podcast Index Feed ID", podcast_value.podcast_index_feed_id],
                ["Suggested Boost Amount (BTC)", podcast_value.suggested],
            ],
            tablefmt="plain",
        )
    )
    click.echo()
    click.echo(
        tabulate(
            [
                [
                    destination.name,
                    f"{destination.split}%",
                    destination.address,
                ]
                for destination in podcast_value.destinations
                if not destination.fee
            ],
            headers=["Recipient", "Split", "Address"],
            tablefmt="simple",
        )
    )
    click.echo()
    click.echo(
        tabulate(
            [
                [
                    destination.name,
                    f"{destination.split}%",
                    destination.address,
                ]
                for destination in podcast_value.destinations
                if destination.fee
            ],
            headers=["Fee", "Amount", "Address"],
            tablefmt="simple",
        )
    )


@cli.command()
@click.pass_context
@click.argument("amount", type=click.IntRange(0))
@click.argument("feed-url")
@click.option("--message")
@click.option("--sender-name", prompt=True)
def boost(ctx, feed_url, amount, message, sender_name):
    feed_service: FeedService = ctx.obj["feed_service"]
    podcast_index_service: Optional[PodcastIndexService] = ctx.obj.get(
        "podcast_index_service"
    )
    lighting_service: LightningService = ctx.obj["lightning_service"]

    if message is None:
        message = click.edit()

    podcast_value = feed_service.podcast_value(feed_url)

    if podcast_value is None and podcast_index_service is not None:
        # Get from Podcast index
        podcast_value = podcast_index_service.podcast_value(feed_url)

    if podcast_value is None:
        click.echo("No Value Block")
        exit(1)

    click.echo(
        tabulate(
            [
                ["Title", podcast_value.podcast_title],
                ["URL", podcast_value.podcast_url],
                ["GUID", podcast_value.podcast_guid],
                ["Podcast Index Feed ID", podcast_value.podcast_index_feed_id],
                ["Amount (sats)", amount],
                ["From", sender_name],
                ["Message", message],
            ],
            tablefmt="plain",
        )
    )

    boost_invoice = BoostInvoice.create(
        amount=amount * 1000,
        podcast_value=podcast_value,
        message=message,
        sender_name=sender_name,
        sender_app_name="BoostCLI",
    )

    click.echo(
        tabulate(
            (
                [
                    ["Payments", None, boost_invoice.amount_after_fees],
                ]
                + [
                    [None, v4v.receiver_name, v4v.amount_msats]
                    for v4v in boost_invoice.payments
                ]
                + [
                    ["Fees", None, boost_invoice.amount_fees],
                ]
                + [
                    [None, v4v.receiver_name, v4v.amount_msats]
                    for v4v in boost_invoice.fees
                ]
                + [
                    ["Total", None, boost_invoice.amount],
                ]
            ),
            headers=["Invoice", "", "msats"],
            tablefmt="fancy_grid",
        )
    )

    if not click.confirm("Send?"):
        return

    table = []
    payments = lighting_service.pay_boost_invoice(boost_invoice)
    with click.progressbar(payments, length=len(podcast_value.destinations)) as bar:
        for payment in bar:
            table.append(
                [
                    payment.payment_hash.hex(),
                    payment.payment_route.total_fees_msat,
                    payment.payment_route.total_amt_msat,
                    len(payment.payment_route.hops),
                ]
            )

    click.echo(
        tabulate(
            table,
            headers=["Payment Hash", "Fee (mSats)", "Total (mSats)", "#hops"],
        )
    )


def print_value(value: ValueForValue, show_boosts=True, show_streamed=True):
    if value.boost:
        action = click.style("Boosted", fg="red")
        if not show_boosts:
            return
    else:
        action = click.style("Streamed", fg="blue")
        if not show_streamed:
            return

    click.secho(f"{value.creation_date}", nl=False)
    click.secho(f" +{int(value.amount_msats / 1000)} ", nl=False, fg="green")
    click.echo(action, nl=False)

    if value.amount_msats_total is not None:
        amount = int(value.amount_msats_total / 1000)
        click.secho(" amount={:d}".format(amount), nl=False)
    if value.sender_app_name:
        click.secho(" app='{}'".format(value.sender_app_name), nl=False)
    if value.sender_name is not None:
        click.secho(" from='{}'".format(value.sender_name), nl=False)
    if value.receiver_name is not None:
        click.secho(" to='{}'".format(value.receiver_name), nl=False)
    if value.podcast_title is not None:
        click.secho(" podcast='{}'".format(value.podcast_title), nl=False)
    if value.episode_title is not None:
        click.secho(" episode='{}'".format(value.episode_title), nl=False)
    if value.timestamp:
        hours = int(value.timestamp / 60 / 60)
        minutes = int((value.timestamp - hours) / 60)
        seconds = int(value.timestamp - hours - minutes)
        click.secho(
            " at='{:0>2d}:{:0>2d}:{:0>2d}'".format(hours, minutes, seconds), nl=False
        )
    if value.message is not None:
        click.secho(" message='{}'".format(value.message), nl=False)
    click.secho()


def read_macaroon(filename):
    with open(filename, "rb") as file_:
        return codecs.encode(file_.read(), "hex")


def read_tlscert(filename):
    with open(filename, "rb") as file_:
        return file_.read()
