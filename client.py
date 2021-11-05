import logging

import discord
import sqlalchemy.orm
from discord.ext import commands

from database import session
from setting import INITIAL_EXTENSIONS


def build_logger() -> logging.Logger:
    sth = logging.StreamHandler()
    flh = logging.FileHandler('sample.log')

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO,
                        handlers=[sth, flh])
    return logging.getLogger(__name__)


class ValorantStoreBot(commands.Bot):
    def __init__(self, prefix: str, intents: discord.Intents):
        super().__init__(prefix, intents=intents)
        for c in INITIAL_EXTENSIONS:
            self.load_extension(c)

        self.database: sqlalchemy.orm.Session = session
        self.logger: logging.Logger = build_logger()

    async def on_ready(self):
        print(f"bot started: {self.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Valorant store"))
