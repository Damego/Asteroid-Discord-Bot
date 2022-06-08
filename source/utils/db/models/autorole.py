from ..requests import RequestClient
from .misc import DictMixin


class GuildAutoRole(DictMixin):
    __slots__ = (
        "_json",
        "_request",
        "guild_id",
        "name",
        "channel_id",
        "content",
        "message_id",
        "type",
        "component",
    )
    name: str
    channel_id: int
    content: str
    message_id: int
    type: str
    component: dict

    def __init__(self, _request: RequestClient, guild_id: int, **kwargs) -> None:
        self._request = _request.autorole
        self._guild_id = guild_id
        super().__init__(**kwargs)

    async def modify(self, **kwargs):
        """
        Modifies autorole

        Parameters:

        name: str
        channel_id: int
        content: str
        message_id: int
        autorole_type: str
        component: dict
        """
        await self._request.modify(self._guild_id, self.name, **kwargs)
        for kwarg, value in kwargs.items():
            setattr(self, kwarg, value)
