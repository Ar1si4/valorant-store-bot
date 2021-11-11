import asyncio
import functools
import logging
import random
from typing import Optional, List, Callable

import discord
import sqlalchemy.orm
from discord.ext import commands

import valclient
from database import session
from database.user import RiotAccount
from setting import INITIAL_EXTENSIONS


def build_logger() -> logging.Logger:
    sth = logging.StreamHandler()
    flh = logging.FileHandler('sample.log')

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO,
                        handlers=[sth, flh])
    return logging.getLogger(__name__)


def get_proxy_url(is_premium: bool):
    if is_premium:
        session_id = "".join(random.choices("0123456789", k=8))
        return {
            'http': f'http://jsoNRCcOS2-cc-any-sid-{session_id}:J1F56mKG@gw.proxy.rainproxy.io:5959',
            'https': f'http://jsoNRCcOS2-cc-any-sid-{session_id}:J1F56mKG@gw.proxy.rainproxy.io:5959'
        }
    return None


class ValorantStoreBot(commands.Bot):
    def __init__(self, prefix: str, intents: Optional[discord.Intents] = None):
        super().__init__(prefix, intents=intents)
        for c in INITIAL_EXTENSIONS:
            self.load_extension(c)

        self.database: sqlalchemy.orm.Session = session
        self.logger: logging.Logger = build_logger()
        self.admins: List[int] = [753630696295235605]

    async def store_content_notify(self):
        while True:
            await asyncio.sleep(60)
            users = self.database.query(User).filter(User.auto_notify_timezone != "").all()
            for user in users:
                try:
                    now_hour = datetime.now().astimezone(user.auto_notify_timezone).hour
                    if now_hour == user.auto_notify_at:
                        if user.auto_notify_flag is True:
                            continue
                        user.auto_notify_flag = True
                        cl = self.new_valorant_client_api(user.is_premium, user.auto_notify_account)
                        try:
                            await self.run_blocking_func(cl.activate)
                        except Exception as e:
                            self.logger.error(f"failed to login valorant client", exc_info=e)
                            self.database.commit()
                            return

                        offers = cl.store_fetch_storefront()
                        for offer_uuid in offers.get("SkinsPanelLayout", {}).get("SingleItemOffers", []):
                            skin = Weapon.get_promised(self.database, offer_uuid, user)
                            embed = discord.Embed(title=skin.display_name, color=0xff0000,
                                                  url=skin.streamed_video if skin.streamed_video else EmptyEmbed,
                                                  description=user.get_text("↑から動画が見れます",
                                                                            "You can watch the video at↑") if skin.streamed_video else EmptyEmbed)
                            embed.set_author(name="valorant shop",
                                             icon_url="https://pbs.twimg.com/profile_images/1403218724681777152/rcOjWkLv_400x400.jpg")
                            embed.set_image(url=skin.display_icon)
                            u = self.get_user(user.id)
                            if not u:
                                u = await self.fetch_user(user.id)
                            await u.send(embed=embed)
                    else:
                        user.auto_notify_flag = False
                except Exception as e:
                    self.logger.error("failed to notify store content", exc_info=e)
            self.database.commit()

    async def run_blocking_func(self, blocking_func: Callable, *args, **kwargs):
        loop = asyncio.get_event_loop()
        function = functools.partial(blocking_func, *args, **kwargs)
        return await loop.run_in_executor(None, function)

    def new_valorant_client_api(self, is_premium: bool,
                                account: RiotAccount) -> valclient.Client:
        proxy = get_proxy_url(is_premium)
        return valclient.Client(region=account.region, auth={
            "username": account.username,
            "password": account.password
        }, proxy=proxy)

    def get_valorant_rank_tier(self, cl: valclient.Client) -> str:
        tier_to_name = ["UNRANKED", "Unused1", "Unused2", "IRON 1", "IRON 2", "IRON 3", "BRONZE 1",
                        "BRONZE 2", "BRONZE 3", "SILVER 1", "SILVER 2", "SILVER 3", "GOLD 1", "GOLD 2",
                        "GOLD 3", "PLATINUM 1", "PLATINUM 2", "PLATINUM 3", "DIAMOND 1", "DIAMOND 2",
                        "DIAMOND 3", "IMMORTAL 1", "IMMORTAL 2", "IMMORTAL 3", "RADIANT"]
        result = cl.fetch_competitive_updates()
        try:
            tier = result["Matches"][0]["TierAfterUpdate"]
        except IndexError:
            return "Failed to get rank tier"
        return tier_to_name[tier]

    async def on_ready(self):
        print(f"bot started: {self.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Valorant store"))

        asyncio.ensure_future(self.store_content_notify())
