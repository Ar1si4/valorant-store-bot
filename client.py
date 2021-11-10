import logging
from typing import Optional

import discord
import sqlalchemy.orm
from discord.ext import commands

import valclient
from cogs.proxies import get_proxy_url
from database import session
from database.user import RiotAccount
from setting import INITIAL_EXTENSIONS


def build_logger() -> logging.Logger:
    sth = logging.StreamHandler()
    flh = logging.FileHandler('sample.log')

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO,
                        handlers=[sth, flh])
    return logging.getLogger(__name__)


class ValorantStoreBot(commands.Bot):
    def __init__(self, prefix: str, intents: Optional[discord.Intents] = None):
        super().__init__(prefix, intents=intents)
        for c in INITIAL_EXTENSIONS:
            self.load_extension(c)

        self.database: sqlalchemy.orm.Session = session
        self.logger: logging.Logger = build_logger()

    def new_valorant_client_api(self, is_premium: bool,
                                account: RiotAccount) -> valclient.Client:
        return valclient.Client(region=account.region, auth={
            "username": account.username,
            "password": account.password
        }, proxy=get_proxy_url(self.database, is_premium, account))

    def get_valorant_rank_tier(self, cl: valclient.Client) -> str:
        tier_to_name = ["UNRANKED", "Unused1", "Unused2", "IRON 1", "IRON 2", "IRON 3", "BRONZE 1",
                        "BRONZE 2", "BRONZE 3", "SILVER 1", "SILVER 2", "SILVER 3", "GOLD 1", "GOLD 2",
                        "GOLD 3", "PLATINUM 1", "PLATINUM 2", "PLATINUM 3", "DIAMOND 1", "DIAMOND 2",
                        "DIAMOND 3", "IMMORTAL 1", "IMMORTAL 2", "IMMORTAL 3", "RADIANT"]
        tier = cl.fetch_competitive_updates()["Matches"][0]["TierAfterUpdate"]
        return tier_to_name[tier]

    async def on_ready(self):
        print(f"bot started: {self.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Valorant store"))
