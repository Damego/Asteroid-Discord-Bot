from .database.consts import StrEnum

__all__ = ["Mentions", "TimeStampsMentions"]


class Mentions(StrEnum):
    """
    Representing strings to mention role/member/etc.
    """

    USER = "<@{id}>"
    ROLE = "<@&{id}>"
    CHANNEL = "<#{id}>"
    COMMAND = "</{name}:{id}>"


class TimeStampsMentions(StrEnum):
    SHORT_TIME = "<t:{timestamp}:t>"
    LONG_TIME = "<t:{timestamp}:T>"
    SHORT_DATE = "<t:{timestamp}:d>"
    LONG_DATE = "<t:{timestamp}:D>"
    SHORT = "<t:{timestamp}:f>"
    LONG = "<t:{timestamp}:F>"
    RELATIVE = "<t:{timestamp}:R>"
