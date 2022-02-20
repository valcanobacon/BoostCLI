import codecs
import os
from dataclasses import dataclass
from posixpath import split
from re import T
from typing import Any, List, Optional

import click
import rich
import tqdm
from google.protobuf.json_format import MessageToJson
from rich import print
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table
from tabulate import tabulate

from src.models import (
    BoostInvoice,
    PodcastValue,
    PodcastValueDestination,
    ValueForValue,
)
from src.services.feed_service import FeedService

from ..providers.podcast_index_provider import PodcastIndexProvider
from ..services.lightning_service import LightningService
from ..services.lightning_service import client_from as lightning_client_from
from ..services.podcast_index_service import PodcastIndexService, SearchType

APP_PUBKEY = "03d55f4d4c870577e98ac56605a54c5ed20c8897e41197a068fd61bdb580efaa67"


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

    ctx.obj["console"] = Console()
    ctx.obj["console_error"] = Console(stderr=True, style="bold red")

    ctx.obj["lightning_service"] = LightningService(
        client=lightning_client_from(
            host=kwargs["address"],
            port=kwargs["port"],
            cert_filepath=kwargs["tlscert"],
            macaroon_filepath=kwargs["macaroon"],
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
@click.pass_context
def boosts_received_watch(ctx, **kwargs):
    lighting_service: LightningService = ctx.obj["lightning_service"]

    for invoice in lighting_service.watch_value_received():
        print_value(invoice)


def find_podcast_value(
    console: Console,
    feed_service: FeedService,
    pi_service: PodcastIndexService,
    search_term: str,
) -> Optional[PodcastValue]:

    pi_search_settings = [
        (SearchType.FEED_URL, "Podcast Index By Feed URL"),
        (SearchType.FEED_ID, "Podcast Index By Feed ID"),
        (SearchType.GUID, "Podcast Index By GUID"),
        (SearchType.ITUNES_ID, "Podcast Index By Itunes ID"),
    ]

    with console.status("By Feed URL") as status:
        podcast_value = feed_service.podcast_value(search_term)

        if podcast_value is None and pi_service is not None:
            for search_type, message in pi_search_settings:
                status.update(message)
                pv = pi_service.podcast_value(search_type, search_term)
                if pv:
                    return pv


@cli.command()
@click.pass_context
@click.argument("search_term")
@click.option("--support-app/--no-support-app", default=True)
def podcast(ctx, search_term, support_app):
    console: Console = ctx.obj["console"]
    console_error: Console = ctx.obj["console_error"]
    feed_service: FeedService = ctx.obj["feed_service"]
    pi_service: Optional[PodcastIndexService] = ctx.obj.get("podcast_index_service")

    podcast_value = find_podcast_value(console, feed_service, pi_service, search_term)
    if podcast_value is None:
        console_error.print(":x: No Value Block")
        exit(1)

    if support_app:
        podcast_value.destinations.append(
            PodcastValueDestination(
                split=1,
                address=APP_PUBKEY,
                name="BoostCLI",
                fee=True,
            )
        )

    podcast_panel = Panel(
        "\n".join(
            (
                x
                for x in (
                    podcast_value.podcast_title,
                    podcast_value.podcast_url,
                    podcast_value.podcast_guid,
                    podcast_value.podcast_index_feed_id
                    and "https://podcastindex.org/podcast/{}".format(
                        podcast_value.podcast_index_feed_id
                    ),
                )
                if x
            )
        ),
        title="Podcast",
    )

    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_column(justify="right")
    for dest in podcast_value.destinations:
        if dest.fee:
            continue
        grid.add_row(dest.name, f"{dest.split}%")

    split_panel = Panel(grid, title="Split")

    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_column(justify="right")
    for dest in podcast_value.destinations:
        if not dest.fee:
            continue
        grid.add_row(dest.name, f"{dest.split}%")

    fee_panel = Panel(grid, title="Fee")

    console.print(Columns([podcast_panel, split_panel, fee_panel], expand=True))


@cli.command()
@click.pass_context
@click.argument("amount", type=click.IntRange(0))
@click.argument("search_term")
@click.option("--message")
@click.option("--sender-name", prompt=True)
@click.option("--support-app/--no-support-app", default=True)
def boost(ctx, search_term, amount, message, sender_name, support_app):
    console: Console = ctx.obj["console"]
    console_error: Console = ctx.obj["console_error"]
    feed_service: FeedService = ctx.obj["feed_service"]
    pi_service: Optional[PodcastIndexService] = ctx.obj.get("podcast_index_service")
    lighting_service: LightningService = ctx.obj["lightning_service"]

    podcast_value = find_podcast_value(console, feed_service, pi_service, search_term)
    if podcast_value is None:
        console_error.print(":x: No Value Block")
        exit(1)

    if message is None:
        message = click.edit()

    if support_app:
        podcast_value.destinations.append(
            PodcastValueDestination(
                split=1,
                address=APP_PUBKEY,
                name="BoostCLI",
                fee=True,
            )
        )

    podcast_panel = Panel(
        "\n".join(
            (
                x
                for x in (
                    podcast_value.podcast_title,
                    podcast_value.podcast_url,
                    podcast_value.podcast_guid,
                    podcast_value.podcast_index_feed_id
                    and "https://podcastindex.org/podcast/{}".format(
                        podcast_value.podcast_index_feed_id
                    ),
                )
                if x
            )
        ),
        title="Podcast",
    )

    table = Table(expand=True, box=None, show_header=False)
    table.add_column()
    table.add_column(justify="right")
    for dest in podcast_value.destinations:
        if dest.fee:
            continue
        table.add_row(dest.name, f"{dest.split}%")

    split_panel = Panel(table, title="Split")

    table = Table(expand=True, box=None, show_header=False)
    table.add_column()
    table.add_column(justify="right")
    for dest in podcast_value.destinations:
        if not dest.fee:
            continue
        table.add_row(dest.name, f"{dest.split}%")

    fee_panel = Panel(table, title="Fee")

    console.print(Columns([podcast_panel, split_panel, fee_panel], expand=True))

    boost_invoice = BoostInvoice.create(
        amount=amount * 1000,
        podcast_value=podcast_value,
        message=message,
        sender_name=sender_name,
        sender_app_name="BoostCLI",
    )

    table = Table(expand=True, box=None)
    table.add_column("Recipient")
    table.add_column("sats", justify="right")
    for value in boost_invoice.payments:
        table.add_row(value.receiver_name, format_msats(value.amount_msats))
    for value in boost_invoice.fees:
        table.add_row(value.receiver_name, format_msats(value.amount_msats))

    invoice_panel = Panel(table, title="Invoice")

    boost_panel = Panel(
        "\n".join(
            (
                x
                for x in (
                    sender_name,
                    "BoostCLI",
                    "{} sats".format(format_msats(boost_invoice.amount)),
                    message,
                )
                if x
            )
        ),
        title="Boost",
    )

    console.print(Columns([invoice_panel, boost_panel], expand=True))

    if not click.confirm("Send?"):
        return

    progress = Progress(auto_refresh=False, expand=True)
    master_task = progress.add_task("overall", total=len(podcast_value.destinations))

    with progress:
        payments = lighting_service.pay_boost_invoice(boost_invoice)
        for index, payment in enumerate(payments):
            hash = payment.payment_hash.hex()
            short_hash = f"{hash[0:8]}...{hash[-8:-1]}"
            fee = format_msats(payment.payment_route.total_fees_msat)
            total = format_msats(payment.payment_route.total_amt_msat)
            hops = len(payment.payment_route.hops)

            if payment.payment_route.total_amt_msat:
                status_icon = ":white_check_mark:"
            else:
                status_icon = ":x:"

            progress.console.print(
                f"{status_icon} {short_hash} fee={fee} total={total} hops={hops}"
            )

            progress.advance(master_task, 1)
            progress.refresh()


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


def format_msats(n: int):
    return "{:,}.{:03}".format(n // 1000, n % 1000)


def read_macaroon(filename):
    with open(filename, "rb") as file_:
        return codecs.encode(file_.read(), "hex")


def read_tlscert(filename):
    with open(filename, "rb") as file_:
        return file_.read()
