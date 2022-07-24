import codecs
import itertools
import os
from typing import Optional

import click
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

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

SATOSHISTREAM_PUBKEYS = [
    "03c457fafbc8b91b462ef0b8f61d4fd96577a4b58c18b50e59621fd0f41a8ae1a4",
]

LNPAY_PUBKEYS = [
    "033868c219bdb51a33560d854d500fe7d3898a1ad9e05dd89d0007e11313588500",
]

HIVE_PUBKEYS = [
    "0396693dee59afd67f178af392990d907d3a9679fa7ce00e806b8e373ff6b70bd8",
]

ASCII = "\n".join(
    (
        "         ,/",
        "       ,'/",
        "     ,' /",
        "   ,'  /_____,",
        " .'____    ,'",
        "      /  ,'",
        "     / ,'",
        "    /,'",
        "   /'",
    )
)

MAX_WIDTH = 128

CONTEXT_SETTINGS = dict(
    show_default=True,
)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--address",
    default="127.0.0.1",
    metavar="ADDRESS",
    help="Address of the LND server",
)
@click.option(
    "--port",
    type=click.IntRange(0),
    default=10009,
    metavar="PORT",
    help="Port of the LND server",
)
@click.option(
    "--macaroon",
    type=click.Path(exists=True),
    default="./admin.macaroon",
    help="Path to the Macaroon for LND for access to the LND server",
)
@click.option(
    "--tlscert",
    type=click.Path(exists=True),
    default="./tls.cert",
    help="Path of the TLS Certificate for connection to the LND server",
)
@click.pass_context
def cli(ctx, **kwargs):
    """
    BoostCLI works by establishing a connection to an LND Server then
    preforming a Command. BoostCLI's first options configure the connection:
    `address`, `port`, `macaroon` and `tlscert`. After the connection
    configuration select a Command to run, `boost`.  Usage instructions all
    Commands can be display by running the -h/--help after the command
    `boostcli boost --help`.

    Running BoostCLI on Raspiblitz:

    $ boostcli --host localhost --port 10009 --macaroon /mnt/hdd/app-data/lnd/data/chain/bitcoin/mainnet/admin.macaroon --tlscert /mnt/hdd/app-data/lnd/tls.cert

    """
    ctx.ensure_object(dict)

    # from: https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md
    # Due to updated ECDSA generated tls.cert we need to let gprc know that
    # we need to use that cipher suite otherwise there will be a handhsake
    # error when we communicate with the lnd rpc server.
    os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"

    console = ctx.obj["console"] = Console()
    console_error = ctx.obj["console_error"] = Console(stderr=True, style="bold red")

    lightning_service = ctx.obj["lightning_service"] = LightningService(
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

    with console.status("Connecting to LND") as status:
        info = lightning_service.get_info()

    if not info:
        console_error.log("failed to connect to LND server")
        ctx.abort()
    else:
        console.print(f"Connected to LND server ({info.alias}), version {info.version}")


@cli.command()
@click.option("--accending/--decending", default=False)
@click.option("--max-number-of-invoices", type=click.IntRange(0), default=10000)
@click.option("--index-offset", type=click.IntRange(0), default=0)
@click.pass_context
def received_boosts(ctx, **kwargs):
    """Display Boosts that have been received."""
    console: Console = ctx.obj["console"]
    console_error: Console = ctx.obj["console_error"]
    lighting_service: LightningService = ctx.obj["lightning_service"]

    try:
        value_received = lighting_service.value_received(
            index_offset=kwargs["index_offset"],
            accending=kwargs["accending"],
            max_number_of_invoices=kwargs["max_number_of_invoices"],
        )

        for value in value_received:
            print_value(value, console)

    except Exception as e:
        console_error.log(e)


@cli.command()
@click.pass_context
def incoming_boosts(ctx, **kwargs):
    """Display Boosts as they are received."""

    console: Console = ctx.obj["console"]
    console_error: Console = ctx.obj["console_error"]
    lighting_service: LightningService = ctx.obj["lightning_service"]

    with console.status("Listening..."):
        try:
            for invoice in lighting_service.watch_value_received():
                print_value(invoice, console)
        except Exception as e:
            console_error.log(e)


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
        pv = feed_service.podcast_value(search_term)
        if pv:
            return pv

        if pi_service is not None:
            for search_type, message in pi_search_settings:
                status.update(message)
                pv = pi_service.podcast_value(search_type, search_term)
                if pv:
                    return pv


@cli.command()
@click.pass_context
@click.argument("search_term")
@click.option(
    "--amount",
    type=click.IntRange(0),
    metavar="SATS",
    help="The number of Satoshis to send",
)
@click.option("--message", help="The message to include in the Boost")
@click.option("--sender-name", help="The name indicating who sent the Boost")
@click.option(
    "--support-app/--no-support-app",
    default=True,
    help="Pay 1% Fee to Support BoostCLI",
)
@click.option(
    "-y", "--yes", is_flag=True, help="Bypasses message and confirmation prompts"
)
def boost(ctx, search_term, amount, message, sender_name, support_app, yes):
    """
    BoostCLI will try to find the Podcast by the given SEARCH_TERM which
    can one of many different things: Feed URL, Podcast Index Feed ID,
    Podcast Index GUID, or ITunes ID. If the Podcast's Feed does not contain
    a value block then the Podcast Index will be checked.

    $ boostcli boost http://mp3s.nashownotes.com/pc20rss.xml
    $ boostcli boost https://podcastindex.org/podcast/920666
    $ boostcli boost 920666
    $ boostcli boost 917393e3-1b1e-5cef-ace4-edaa54e1f810
    """
    console: Console = ctx.obj["console"]
    console_error: Console = ctx.obj["console_error"]
    feed_service: FeedService = ctx.obj["feed_service"]
    pi_service: Optional[PodcastIndexService] = ctx.obj.get("podcast_index_service")
    lighting_service: LightningService = ctx.obj["lightning_service"]

    pv = find_podcast_value(console, feed_service, pi_service, search_term)
    if pv is None:
        console_error.print(
            f':broken_heart: Failed to locate value by search_term="{search_term}"'
        )
        exit(1)

    if support_app:
        pv.destinations.append(
            PodcastValueDestination(
                split=1,
                address=APP_PUBKEY,
                name="BoostCLI",
                fee=True,
            )
        )

    table_split = Table(
        title=Text("Split", style="yellow"), box=None, show_header=False
    )
    table_split.add_column(style="yellow")
    table_split.add_column(justify="right", style="yellow")
    for dest in pv.destinations:
        if dest.fee:
            continue
        table_split.add_row(dest.name, f"{dest.split}%")

    table_fee = Table(
        title=Text("Fees", style="red"), box=None, show_header=False, style="red"
    )
    table_fee.add_column(style="red")
    table_fee.add_column(justify="right", style="red")
    for dest in pv.destinations:
        if not dest.fee:
            continue
        table_fee.add_row(dest.name, f"{dest.split}%")

    metadata_text = Text()
    if pv.podcast_title:
        metadata_text.append(f"{pv.podcast_title}\n", style="bold yellow")
    if pv.episode_title:
        metadata_text.append(f"{pv.episode_title}\n", style="bold yellow")
    if pv.podcast_guid:
        metadata_text.append(f"{pv.podcast_guid}\n")
    if pv.podcast_url:
        metadata_text.append(f"{pv.podcast_url}\n")
    if pv.podcast_index_feed_id:
        metadata_text.append(
            f"https://podcastindex.org/podcast/{pv.podcast_index_feed_id}\n"
        )

    ascii_text = Text(ASCII, style="bold yellow")

    grid = Table.grid(padding=2)
    grid.add_column()
    grid.add_column()

    g = Table.grid()
    g.add_column()
    g.add_row(metadata_text)
    g.add_row(Columns([table_split, table_fee]))
    grid.add_row(ascii_text, g)

    console.print(Panel.fit(grid, title="Podcast", width=MAX_WIDTH))

    if not message and sender_name and amount and not yes:
        Prompt.ask("Push any key to continue", default=0, show_default=False)

    if yes:
        if amount is None:
            print("--yes error: Define an amount using --amount !")
            return
        if sender_name is None:
            sender_name = "Anonymous"

    if amount is None:
        amount = IntPrompt.ask(Text("amount (sats)", style="bold yellow"))

    if sender_name is None:
        sender_name = Prompt.ask(
            Text("Sender name", "bold cyan"), default=0, show_default=False
        )

    if message is None and not yes:
        message = click.edit("Write message... 300 characters max")
        message = message[:300]

    boost_invoice = BoostInvoice.create(
        amount=amount * 1000,
        podcast_value=pv,
        message=message,
        sender_name=sender_name,
        sender_app_name="BoostCLI",
    )

    table = Table(expand=True, box=None)
    table.add_column("Recipient")
    table.add_column("Address", justify="center")
    table.add_column("sats", justify="right")
    for value in itertools.chain(boost_invoice.payments, boost_invoice.fees):
        address = shorten(value.receiver_address)

        if value.receiver_address in LNPAY_PUBKEYS:
            address = "HIVE"
        if value.receiver_address in SATOSHISTREAM_PUBKEYS:
            address = "SS"
        if value.receiver_address in LNPAY_PUBKEYS:
            address = "LNPAY"

        if value.custom_key and value.custom_value:
            if value.custom_key in [696969, 112111100, 818818]:
                address = f"{address} {value.custom_value.decode('utf8')}"

        table.add_row(value.receiver_name, address, format_msats(value.amount_msats))

    invoice_panel = Panel(table, title="Invoice", style="yellow")

    boost_text = Text()
    boost_text.append(sender_name)
    boost_text.append("\n")
    boost_text.append(
        "{} sats".format(format_msats(boost_invoice.amount)), style="bold"
    )
    boost_text.append("\n")
    boost_text.append("\n")

    if message:
        boost_text.append(message, style="bold")

    boost_panel = Panel(
        boost_text,
        title="Boost",
        style="cyan",
    )

    console.print(invoice_panel, width=MAX_WIDTH)
    console.print(boost_panel, width=MAX_WIDTH)

    if not yes:
        if not Confirm.ask("Send?"):
            return

    progress = Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(bar_width=MAX_WIDTH),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
    )
    master_task = progress.add_task(
        pv.destinations[0].name, total=len(pv.destinations), width=MAX_WIDTH
    )

    with progress:
        payments = lighting_service.pay_boost_invoice(boost_invoice)
        for i, payment in enumerate(payments):
            dest = pv.destinations[i]

            progress.refresh()

            hash = payment.payment_hash.hex()
            short_hash = shorten(hash)
            fee = format_msats(payment.payment_route.total_fees_msat)
            total = format_msats(payment.payment_route.total_amt_msat)
            hops = len(payment.payment_route.hops)

            if payment.payment_error:
                status = f" :x: [bold yellow]{dest.name}[/bold yellow] {short_hash} [bold red]{payment.payment_error}[/bold red]"
            else:
                status = f" :white_check_mark: [bold yellow]{dest.name}[/bold yellow] {short_hash} fee={fee} total={total} hops={hops}"

            progress.console.print(status)

            progress.advance(master_task, 1)

            if i < len(pv.destinations) - 1:
                next_dest = pv.destinations[i + 1]
                progress.update(master_task, description=next_dest.name)


def print_value(
    value: ValueForValue, console: Console, show_boosts=True, show_streamed=True
):
    if value.boost:
        action = click.style("Boosted", fg="cyan")
        if not show_boosts:
            return
    else:
        action = click.style("Streamed", fg="yellow")
        if not show_streamed:
            return

    text = Text()
    text.append(str(value.creation_date))
    text.append(" ")
    text.append(str(int(value.amount_msats / 1000)), style="green")
    text.append(" ")
    text.append(str(action))
    text.append(" ")

    def append_item(key, value, value_style="bold"):
        text.append(" ")
        text.append(str(key))
        text.append("=")
        text.append('"')
        text.append(f"{str(value)}", style=value_style)
        text.append('"')

    if value.amount_msats_total is not None:
        amount = int(value.amount_msats_total / 1000)
        append_item("amount", f"{amount:d}", "bold green")

    if value.sender_app_name:
        append_item("app", f"{value.sender_app_name}")

    if value.sender_name is not None:
        append_item("from", f"{value.sender_app_name}")

    if value.receiver_name is not None:
        append_item("to", f"{value.receiver_name}")

    if value.podcast_title is not None:
        append_item("podcast", f"{value.podcast_title}")

    if value.episode_title is not None:
        append_item("episode", f"{value.episode_title}")

    if value.timestamp:
        hours = int(value.timestamp / 60 / 60)
        minutes = int((value.timestamp - hours) / 60)
        seconds = int(value.timestamp - hours - minutes)
        append_item(
            "at",
            "{:0>2d}:{:0>2d}:{:0>2d}".format(hours, minutes, seconds),
        )
    if value.message is not None:
        append_item("message", f"{value.message}", "bold cyan")

    console.print(text)


def shorten(pubkey: str, segment_length=8, seperator=" ... ") -> str:
    if len(pubkey) < segment_length * 2:
        return pubkey
    prefix = pubkey[0:segment_length]
    suffix = pubkey[-1 * segment_length :]
    return f"{prefix}{seperator}{suffix}"


def format_msats(n: int):
    sats = n // 1000
    msats = n % 1000
    return f"{sats:,} .{msats:03}".replace(",", " ")


def read_macaroon(filename):
    with open(filename, "rb") as file_:
        return codecs.encode(file_.read(), "hex")


def read_tlscert(filename):
    with open(filename, "rb") as file_:
        return file_.read()
