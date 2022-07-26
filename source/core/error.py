class BotException(Exception):
    def __init__(self, code: int):
        self.code = code

    @property
    def message(self):
        return {
            # Autoroles errors
            100: "AUTOROLE_NOT_FOUND",
            101: "CHANNEL_NOT_FOUND",
            102: "MESSAGE_NOT_FOUND",
            103: "OPTION_NOT_FOUND",
            104: "OPTIONS_LIMIT",
            105: "BUTTONS_LIMIT",
            106: "BUTTON_NOT_FOUND",
            107: "ON_JOIN_ROLE_NOT_FOUND",
            108: "MESSAGE_WITHOUT_BUTTONS",
            109: "ROLE_ALREADY_EXIST",
            110: "NO_AUTO_ON_JOIN_ROLES",
        }.get(self.code, f"Unknown Error with code: {self.code}")
