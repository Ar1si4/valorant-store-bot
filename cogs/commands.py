import random

import discord
from discord import Interaction
from discord.ext import commands
from discord.ext.commands import Context

from client import ValorantStoreBot
from database import User


class CommandsHandler(commands.Cog):
    def __init__(self, bot: ValorantStoreBot):
        self.bot = bot

    @commands.command("randommap", aliases=["ランダムマップ"])
    async def random_map(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)
        if user.language == "ja-JP":
            maps = ["アセント", "スプリット", "バインド", "ブリーズ", "アイスボックス", "ヘイブン", "フラクチャー"]
        else:
            maps = ["Icebox", "Breeze", "Ascent", "Haven", "Split", "Bind", "Fracture"]
        await ctx.send(random.choice(maps))

    @commands.command("language", aliases=["言語"])
    async def change_language(self, ctx: Context):
        view = discord.ui.View(timeout=60)

        def button_pushed_lang(lang: str):
            async def button_pushed(interaction: Interaction):
                db_user = User.get_promised(self.bot.database, interaction.user.id)
                db_user.language = lang
                self.bot.database.commit()
                await interaction.channel.send(db_user.get_text("更新しました", "updated"))

            return button_pushed

        en_button = discord.ui.Button(label="English")
        en_button.callback = button_pushed_lang("en-US")

        ja_button = discord.ui.Button(label="日本語")
        ja_button.callback = button_pushed_lang("ja-JP")

        view.add_item(en_button)
        view.add_item(ja_button)
        await ctx.send(content="JA) ご自身の使用している言語を選択してください\nEN) Select the language you are using", view=view)


def setup(bot: ValorantStoreBot):
    bot.add_cog(CommandsHandler(bot))
