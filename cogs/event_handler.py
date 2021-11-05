import traceback

from discord.ext import commands

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
