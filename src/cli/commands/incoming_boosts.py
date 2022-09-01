import click
from rich.console import Console

from src.services.lightning_service import LightningService

from ..print_value import print_value


@click.command()
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
