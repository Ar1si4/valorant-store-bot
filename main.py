import os

import discord

from client import ValorantStoreBot

if __name__ == "__main__":
    bot = ValorantStoreBot("" )
    bot.run(os.getenv("DISCORD_TOKEN"))
