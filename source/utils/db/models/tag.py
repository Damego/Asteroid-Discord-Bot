from ..requests import RequestClient
from .misc import DictMixin


class GuildTag(DictMixin):
    __slots__ = (
        "_json",
        "_request",
        "guild_id",
        "name",
        "author_id",
        "is_embed",
        "title",
        "description",
        "created_at",
        "last_edited_at",
        "uses_count",
    )
    name: str
    author_id: int
    is_embed: bool
    title: str
    description: str
    created_at: int
    last_edited_at: int
    uses_count: int

    def __init__(self, _request: RequestClient, guild_id: int, **kwargs) -> None:
        self._request = _request.tags
        self.guild_id = guild_id
        super().__init__(kwargs)

    async def modify(self, **kwargs):
        """
        Parameters:
        name: str
        author_id: int
        is_embed: bool
        title: str
        description: str
        created_at: int
        last_edited_at: int
        uses_count: int
        """
        await self._request.modify(self.guild_id, self.name, **kwargs)
        for kwarg, value in kwargs.items():
            setattr(self, kwarg, value)
