import click
from rich.console import Console
from rich.text import Text

from src.models import ValueForValue


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
