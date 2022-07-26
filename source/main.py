from os import getenv

import interactions
from core import Asteroid
from dotenv import load_dotenv

from utils.functions import load_extensions  # isort: skip

load_dotenv()

client = Asteroid(getenv("TOKEN"), getenv("MONGO_URL"), intents=interactions.Intents.ALL)
load_extensions(client, "extensions")


@client.event
async def on_ready():
    print("Bot ready")


client.start()
