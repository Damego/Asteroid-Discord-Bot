from enum import Enum
from typing import TypeAlias

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

__all__ = ["AsyncMongoClient", "StrEnum", "Language", "OperatorType", "DocumentType"]

AsyncMongoClient: TypeAlias = MongoClient | AsyncIOMotorClient


class StrEnum(str, Enum):
    ...


class Language(StrEnum):
    """
    Representing supported languages
    """

    RUSSIAN = "ru"
    ENGlISH = "en-US"


class OperatorType(StrEnum):
    SET = "$set"
    UNSET = "$unset"
    PUSH = "$push"
    PULL = "$pull"


class DocumentType(StrEnum):
    SETTINGS = "configuration"
    CONFIGURATION = "configuration"
    AUTOROLES = "autoroles"
    TAGS = "tags"
    EMOJI_BOARDS = "emoji_boards"
    PRIVATE_VOICE = "private_voice"
    LEVELING = "leveling"
