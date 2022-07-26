import json
from pathlib import Path

__all__ = ["Locale", "LocaleManager"]


class Locale:
    __slots__ = ("commands", "errors")

    def __init__(self, commands: dict[str, str], errors: dict[str, str]):
        self.commands = commands
        self.errors = errors

    def __getitem__(self, item: str) -> str:
        if item.isdigit():
            return self.errors.get(item, item)
        return self.commands.get(item, item)


class LocaleManager:
    __slots__ = ("locales", "path")

    def __init__(self, path: str):
        self.locales: dict[str, Locale] = {}
        self.path = path

        self.__load_localisation()

    def __load_localisation(self):
        path = Path(self.path)
        for folder in path.iterdir():
            temp = {}
            for file in folder.iterdir():
                name = file.name[:-5]
                with open(file) as _file:
                    temp[name] = json.load(_file)
            self.locales[folder.name] = Locale(**temp)

    def __getitem__(self, item: str) -> Locale:
        return self.locales[item]
