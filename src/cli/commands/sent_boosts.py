import click
from rich.console import Console

from src.services.lightning_service import LightningService

from ..print_value import print_value


@click.command()
@click.option("--accending/--decending", default=False)
@click.option("--max-number-of-payments", type=click.IntRange(0), default=10000)
@click.option("--index-offset", type=click.IntRange(0), default=0)
@click.pass_context
def sent_boosts(ctx, **kwargs):
    """Display Boosts that have been sent."""
    console: Console = ctx.obj["console"]
    console_error: Console = ctx.obj["console_error"]
    lighting_service: LightningService = ctx.obj["lightning_service"]

    try:
        value_received = lighting_service.value_sent(
            index_offset=kwargs["index_offset"],
            accending=not kwargs["accending"],
            max_payments=kwargs["max_number_of_payments"],
        )

        for value in value_received:
            print_value(value, console)

    except Exception as e:
        console_error.log(e)
