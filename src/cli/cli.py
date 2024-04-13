import os

import click
from rich.console import Console

from src.services.feed_service import FeedService

from src.providers.podcast_index_provider import PodcastIndexProvider
from src.services.lightning_service import LightningService
from src.services.lightning_service import client_from as lightning_client_from
from src.services.podcast_index_service import PodcastIndexService


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
    help="Path to the Macaroon for LND for access to the LND server",
    default="admin.macaroon"
)
@click.option(
    "--tlscert",
    type=click.Path(exists=True),
    help="Path of the TLS Certificate for connection to the LND server",
    default="tls.cert"
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

    \b
    $ boostcli --macaroon /mnt/hdd/app-data/lnd/data/chain/bitcoin/mainnet/admin.macaroon --tlscert /mnt/hdd/app-data/lnd/tls.cert

    """
    ctx.ensure_object(dict)

    # from: https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md
    # Due to updated ECDSA generated tls.cert we need to let gprc know that
    # we need to use that cipher suite otherwise there will be a handhsake
    # error when we communicate with the lnd rpc server.
    os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"

    console = ctx.obj["console"] = Console()
    console_error = ctx.obj["console_error"] = Console(stderr=True, style="bold red")

    lightning_service = ctx.obj["lightning_service"] = lightning_client_from(
        host=kwargs["address"],
        port=kwargs["port"],
        cert_filepath=kwargs["tlscert"],
        macaroon_filepath=kwargs["macaroon"],
    )

    ctx.obj["podcast_index_service"] = PodcastIndexService(
        provider=PodcastIndexProvider(
            user_agent="Boost Account",
            api_key="5K3YPBAKHWAEBR6R9ZNY",
            api_secret="zrnd^d9HtMH4aH#vBQSPsSKES6$pVtv^ra2dkQFq",
        )
    )

    ctx.obj["feed_service"] = FeedService()

    with console.status("Connecting to LND"):
        info = lightning_service.get_info()

    if not info:
        console_error.log("failed to connect to LND server")
        ctx.abort()
    else:
        console.print(f"Connected to LND server ({info.alias}), version {info.version}")
