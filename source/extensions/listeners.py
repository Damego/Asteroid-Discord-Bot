from interactions import CommandContext, Extension, Guild, LibraryException  # noqa
from interactions import extension_listener as listener

from core import Asteroid, BotException  # noqa isort: skip


class Listeners(Extension):
    def __init__(self, client: Asteroid):
        # I should add type annotation since current annotation is `interactions.Client`
        self.client: Asteroid = client

    @listener
    async def on_guild_delete(self, guild: Guild):
        # TODO: Remove guild from database
        ...

    # @listener
    # async def on_command_error(self, ctx: CommandContext, error: LibraryException | BotException | Exception):
    # if isinstance(error, LibraryException):
    #     await ctx.send(f"Library exception: {error.message}")  # TODO: Rework this and add localisation
    # elif isinstance(error, BotException):
    #     await ctx.send(f"Bot Exception: {error.message}")  # TODO: Add localisation
    # else:  # What it can be?
    #     await ctx.send(f"Unknown exception: {error}")


def setup(client):
    Listeners(client)
