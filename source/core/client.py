from interactions import Client, Snowflake, get

from .database import DataBaseClient
from .locale import Locale, LocaleManager

__all__ = ["Asteroid"]


class Asteroid(Client):
    def __init__(self, bot_token: str, mongodb_url: str, **kwargs):
        super().__init__(bot_token, **kwargs)
        self.database = DataBaseClient(mongodb_url)
        self.locale = LocaleManager("locale")

    async def get_locale(self, guild_id: int | Snowflake) -> Locale:
        guild_data = await self.database.get_guild(
            int(guild_id) if isinstance(guild_id, Snowflake) else guild_id
        )
        return self.locale[guild_data.settings.language]

    async def get(self, *args, **kwargs):
        return await get(self, *args, **kwargs)
