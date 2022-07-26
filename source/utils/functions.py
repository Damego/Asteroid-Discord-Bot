import re
from pathlib import Path

from core import Asteroid
from interactions import ActionRow, Color, Embed, EmbedField, Emoji

__all__ = ["load_extensions", "components_from_dict", "get_emoji_from_str", "create_embed"]


def load_extensions(client: Asteroid, path: str):
    path = Path(path)
    for extension in path.iterdir():
        name = extension.name
        if name == "__pycache__":
            continue
        if name.endswith(".py"):
            client.load(f"{path}.{name[:-3]}")
        elif extension.is_dir():
            client.load(f"{path}.{name}")


def components_from_dict(components: list[dict]) -> list[ActionRow]:
    return [ActionRow(**action_row) for action_row in components]


def get_emoji_from_str(emoji: str | None) -> Emoji | None:
    if emoji is None:
        return
    if re.fullmatch("<:[a-zA-Z0-9_]+:[0-9]+>", emoji):
        emoji = emoji.replace("<:", "").replace(">", "")
        name, emoji_id = map(int, emoji.split(":"))
        return Emoji(name=name, id=emoji_id)
    else:
        if len(emoji) > 1:
            return
        return Emoji(name=emoji)  # btw its still can be any symbol so its bad


def create_embed(
    description: str = None, title: str = None, fields: list[EmbedField] = None
) -> Embed:
    return Embed(title=title, description=description, fields=fields, color=Color.blurple())
