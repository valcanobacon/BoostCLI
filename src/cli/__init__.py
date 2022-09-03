from .cli import cli
from .commands.boost import boost
from .commands.received_boosts import received_boosts
from .commands.incoming_boosts import incoming_boosts
from .commands.sent_boosts import sent_boosts


# Add Commands to CLI
cli.add_command(boost)
cli.add_command(received_boosts)
cli.add_command(incoming_boosts)
cli.add_command(sent_boosts)
