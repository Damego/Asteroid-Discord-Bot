from collections import defaultdict
from typing import Generic, Type, TypeAlias, TypeVar

ID: TypeAlias = str
_T = TypeVar("_T")


class Storage(Generic[_T]):
    __slots__ = "values"

    def __repr__(self):
        return f"<{self.__class__.__name__} contain {len(self.values)} items>"

    def __init__(self):
        self.values: dict[ID, _T] = {}

    def __setitem__(self, key: ID, value: _T):
        self.values[key] = value

    def __getitem__(self, key: ID) -> _T:
        return self.values.get(key)

    def __delitem__(self, key: ID):
        self.values.__delitem__(key)

    def items(self) -> dict[ID, _T]:
        return self.values.items()


class Cache:
    __slots__ = "storages"

    def __init__(self):
        self.storages: defaultdict[Type[_T], Storage[_T]] = defaultdict(Storage)

    def __getitem__(self, item: Type[_T]) -> Storage[_T]:
        return self.storages[item]


cache = Cache()
