from functools import wraps
from string import ascii_uppercase
from typing import TYPE_CHECKING, Callable

import attrs

from ..consts import OperatorType

if TYPE_CHECKING:
    from ..client import DataBaseClient


class MISSING:
    ...


@attrs.define(eq=False, init=False)
class DictSerializerMixin:
    _json: dict = attrs.field(init=False, repr=False)

    def __init__(self, kwargs_dict: dict = None, **other_kwargs):
        kwargs = kwargs_dict or other_kwargs
        self._json = kwargs.copy()
        database = kwargs.pop("_database", None)
        passed_kwargs = {}
        attribs: tuple[attrs.Attribute, ...] = self.__attrs_attrs__
        for attrib in attribs:
            if not attrib.init:
                continue
            metadata = attrib.metadata
            attr_name = attrib.name
            if (value := kwargs.get(metadata["alias"], MISSING)) is MISSING:
                if (value := kwargs.get(attr_name, MISSING)) is MISSING:
                    value = MISSING
            if value is not None and value is not MISSING:
                if isinstance(value, list):
                    for item in value:
                        if metadata["add_database"]:
                            item["_database"] = database
                        if metadata["add_guild_id"]:
                            item["guild_id"] = kwargs.get("guild_id", MISSING)
                elif isinstance(value, dict):
                    if metadata["add_database"]:
                        value["_database"] = database
                    if metadata["add_guild_id"]:
                        value["guild_id"] = kwargs.get("guild_id", MISSING)
            elif attrib.default is not attrs.NOTHING:
                value = attrib.default
                if isinstance(value, attrs.Factory):  # type: ignore
                    value = value.factory()  # type: ignore
            else:
                value = None

            passed_kwargs[attr_name] = value
        self.__attrs_init__(**passed_kwargs)


@attrs.define(eq=False, init=False)
class DataBaseSerializerMixin(DictSerializerMixin):
    _database: "DataBaseClient" = attrs.field(init=False, repr=False)
    guild_id: int = attrs.field(init=False, repr=False)

    def __init__(self, kwargs_dict: dict = None, **other_kwargs):
        kwargs = kwargs_dict or other_kwargs
        self._database = kwargs.get("_database")
        self.guild_id = kwargs.get("guild_id")
        super().__init__(**kwargs)

    async def update(self):
        _json = attrs.asdict(
            self, filter=lambda attr, value: attr.name not in ("_json", "_database", "guild_id")
        )
        data = {
            key: value
            for key, value in _json.items()
            if (self._json.get(key) is not None and self._json[key] != value)
            or (self._json.get(key) is None and key not in ["id", "guild_data"])
            or (value is not self._json.get(key))  # TODO: Lists can had same value and its bad.
        }
        guild_id = self._json["guild_id"]
        model_name = str(self.__class__.__name__)
        match model_name:
            case "GuildUser":
                await self._database.update_user(self._json["id"], guild_id, data)
            case "GuildSettings":
                await self._database.update_guild(guild_id, "configuration", OperatorType.SET, data)
            case "GuildAutoRole" | "GuildTag" | "GuildEmojiBoard":
                key = model_name[5:].lower() + "s"
                document = {"_id": key, f"{key}.name": self._json["name"]}
                payload = {f"{key}.$.{k}": value for k, value in _json.items()}
                await self._database.update_guild(guild_id, document, OperatorType.SET, payload)
            case "GuildPrivateVoice" | "GuildLeveling":
                key = model_name
                for char in key:
                    if char in ascii_uppercase:
                        key = key.replace(char, f"_{char.lower()}", 1)
                await self._database.update_guild(guild_id, key, OperatorType.SET, data)

        self._json = _json
        self._json["guild_id"] = guild_id


def convert_list(obj: Callable):
    def wrapper(list_data: list):
        if list_data is MISSING or list_data is None:
            return []
        return [obj(**data) for data in list_data]

    return wrapper


def convert_int(num: int | float | None):
    if num is None or num is MISSING:
        return MISSING
    return int(num)


define_defaults = dict(kw_only=True, eq=False, init=False)


@wraps(attrs.define)
def define(**kwargs):
    return attrs.define(**kwargs, **define_defaults)


@wraps(attrs.field)
def field(
    converter=None,
    default=attrs.NOTHING,
    add_database: bool = False,
    add_guild_id: bool = False,
    alias: str = None,
    **kwargs,
):
    metadata = dict(add_database=add_database, alias=alias, add_guild_id=add_guild_id)

    return attrs.field(converter=converter, default=default, metadata=metadata, **kwargs)
