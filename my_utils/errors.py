class NotConnectedToVoice(Exception):
    pass


class TagNotFound(Exception):
    pass


class ForbiddenTag(Exception):
    pass


class NotTagOwner(Exception):
    pass


class UIDNotBinded(Exception):
    pass


class GenshinDataNotPublic(Exception):
    pass


class GenshinAccountNotFound(Exception):
    pass


class CogDisabledOnGuild(Exception):
    pass


class CommandDisabled(Exception):
    """For disabled commands for guild"""

    def __init__(self, message: str = None):
        self.message = message
