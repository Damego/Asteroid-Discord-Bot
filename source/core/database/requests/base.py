from ..consts import AsyncMongoClient
from .guild_requests import GuildRequests


class Requests:
    def __init__(self, client: AsyncMongoClient):
        self.guild = GuildRequests(client)
