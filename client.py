import discord
from discord.ext import commands
from valorant_api import SyncValorantApi

from database import session
from setting import INITIAL_EXTENSIONS


class ValorantStoreBot(commands.Bot):
    def __init__(self, prefix: str, intents: discord.Intents):
        super().__init__(prefix, intents=intents)
        for c in INITIAL_EXTENSIONS:
            self.load_extension(c)
        self.db = session

    async def on_ready(self):
        print(f"bot started: {self.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Valorant store"))
