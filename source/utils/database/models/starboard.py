from typing import Dict, List

from ..requests import RequestClient
from .misc import DictMixin


class GuildStarboard(DictMixin):
    __slots__ = (
        "_json",
        "_request",
        "guild_id",
        "channel_id",
        "is_enabled",
        "limit",
        "messages",
        "blacklist",
    )
    channel_id: int
    is_enabled: bool
    limit: int
    messages: Dict[str, Dict[str, int]]
    blacklist: "StarBoardBlackList"

    def __init__(self, _request: RequestClient, guild_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._request = _request.starboard
        self.guild_id = guild_id
        self.messages = {} if self.messages is None else self.messages
        self.blacklist = StarBoardBlackList(**kwargs.get("blacklist", {}))

    @property
    def is_ready(self):
        return self.channel_id is not None and self.limit is not None and self.is_enabled

    async def add_starboard_message(self, message_id: int, starboard_message_id: int):
        await self._request.add_message(self.guild_id, message_id, starboard_message_id)
        self.messages[str(message_id)] = {"starboard_message": starboard_message_id}

    async def modify(self, **kwargs):
        """
        Parameters:

        is_enabled: bool
        channel_id: int
        limit: int
        """
        await self._request.modify(self.guild_id, **kwargs)
        for kwarg, value in kwargs.items():
            setattr(self, kwarg, value)

    async def add_member_to_blacklist(self, member_id: int):
        await self._request.add_member_to_blacklist(self.guild_id, member_id)
        self.blacklist.members.append(member_id)

    async def remove_member_from_blacklist(self, member_id: int):
        await self._request.remove_member_from_blacklist(self.guild_id, member_id)
        self.blacklist.members.remove(member_id)

    async def add_channel_to_blacklist(self, channel_id: int):
        await self._request.add_channel_to_blacklist(self.guild_id, channel_id)
        self.blacklist.channels.append(channel_id)

    async def remove_channel_from_blacklist(self, channel_id: int):
        await self._request.remove_channel_from_blacklist(self.guild_id, channel_id)
        self.blacklist.channels.remove(channel_id)

    async def add_role_to_blacklist(self, role_id: int):
        await self._request.add_role_to_blacklist(self.guild_id, role_id)
        self.blacklist.roles.append(role_id)

    async def remove_role_from_blacklist(self, role_id: int):
        await self._request.remove_role_from_blacklist(self.guild_id, role_id)
        self.blacklist.roles.remove(role_id)


class StarBoardBlackList(DictMixin):
    __slots__ = ("_json", "members", "channels", "roles")
    members: List[int]
    channels: List[int]
    roles: List[int]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        for slot in self.__slots__:
            if not slot.startswith("_") and slot not in kwargs:
                setattr(self, slot, list())

    @property
    def is_empty(self):
        return not self.members and not self.roles and not self.channels
