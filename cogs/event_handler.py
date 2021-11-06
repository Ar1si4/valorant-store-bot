import traceback

import discord
from discord.ext import commands

import database.guild
from client import ValorantStoreBot


class EventHandler(commands.Cog):
    def __init__(self, bot: ValorantStoreBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CommandInvokeError):  # コマンド実行時にエラーが発生したら
            orig_error = getattr(error, "original", error)
            error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
            self.bot.logger.error(error_msg)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        database.Guild.get_promised(self.bot.database, guild.id)

        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    description="初めまして、私はValorantのショップにある毎日ローテする４つのスキンをコマンド一つで表示するためのBOTです！ \nいちいちログインして確認するのがめんどくさいので作りました。 \nstore, shop, ショップ 等のコマンドを入力することで取得することができます。 \n勿論、個人チャットでも使用可能です",
                    color=0xff0000)
                embed.set_author(name="Valorant store bot", url="https://valorant.sakura.rip",
                                 icon_url="https://pbs.twimg.com/profile_images/1403218724681777152/rcOjWkLv_400x400.jpg")
                embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/1403218724681777152/rcOjWkLv_400x400.jpg")

                await channel.send(embed=embed)
                await channel.send(content="言語を変更することができます！\n[言語]コマンドをご利用ください\n\nNow you can change the language!\nPlease use the\n[language] command")
                return


def setup(bot: ValorantStoreBot):
    bot.add_cog(EventHandler(bot))
