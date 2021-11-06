import asyncio
import random
from typing import Union, Callable

import discord
from discord import Interaction
from discord.embeds import EmptyEmbed
from discord.ext import commands
from discord.ext.commands import Context

from client import ValorantStoreBot, new_valorant_client_api
from database import User, Weapon
from database.user import RiotAccount


class CommandsHandler(commands.Cog):
    def __init__(self, bot: ValorantStoreBot):
        self.bot = bot

    async def list_account_and_execute(self, ctx: Context, func: Callable):
        user = User.get_promised(self.bot.database, ctx.message.author.id)

        view = discord.ui.View(timeout=240)
        accounts = user.riot_accounts
        if len(accounts) == 1:
            await func(view)(type("Interaction", (object,), {
                "data": {"values": [accounts[0].game_name]}
            }))
            return
        menu = discord.ui.Select(options=[
            discord.SelectOption(
                label=account.game_name
            ) for account in accounts
        ])

        menu.callback = func(view)
        view.add_item(menu)
        await ctx.send(content=user.get_text("実行するアカウント情報を選択してください", "Select the account to execute"),
                       view=view)

        view_stat = await view.wait()
        if view_stat:
            await ctx.send(user.get_text("４分以上応答がないため、登録のプロセスを終了します。",
                                         "Since there is no response for more than 4 minutes, the registration process is terminated."))

    @commands.command("nightmarket", aliases=["ナイトストア"])
    async def fetch_night_market(self, ctx: Context):
        def wrapper(view: discord.ui.View):
            async def select_account_region(interaction: Interaction):
                account: RiotAccount = self.bot.database.query(RiotAccount).filter(
                    RiotAccount.game_name == interaction.data["values"][0]).first()
                cl = new_valorant_client_api(account.region, account.username, account.password)
                try:
                    cl.activate()
                except Exception as e:
                    self.bot.logger.error(f"failed to login valorant client", exc_info=e)
                    await ctx.send(User.get_promised(self.bot.database, ctx.message.author.id).get_text(
                        "ログイン情報の更新が必要です。パスワードの変更などをした場合にこのメッセージが表示されます。「登録」コマンドを利用してください",
                        "You need to update your login credentials. This message will appear if you have changed your password. Please use the [register] command."))
                    view.stop()
                    return
                user = User.get_promised(self.bot.database, ctx.message.author.id)
                offers = cl.store_fetch_storefront()
                for offer in offers.get("BonusStore", {}).get("BonusStoreOffers", []):
                    skin = Weapon.get_promised(self.bot.database, offer["Offer"]["Rewards"][0]["ItemID"], user)
                    embed = discord.Embed(title=skin.display_name, color=0xff0000,
                                          url=skin.streamed_video if skin.streamed_video else EmptyEmbed,
                                          description=user.get_text(
                                              f'{list(offer["Offer"]["Cost"].values())[0]}→{list(offer["DiscountCosts"].values())[0]}({offer["DiscountPercent"]}%off) ',
                                              f'{list(offer["Offer"]["Cost"].values())[0]}→{list(offer["DiscountCosts"].values())[0]}({offer["DiscountPercent"]}%off) ') if skin.streamed_video else EmptyEmbed)
                    embed.set_author(name="valorant shop",
                                     icon_url="https://pbs.twimg.com/profile_images/1403218724681777152/rcOjWkLv_400x400.jpg")
                    embed.set_image(url=skin.display_icon)
                    await ctx.send(embed=embed)
                    view.stop()

            return select_account_region

        await self.list_account_and_execute(ctx, wrapper)

    @commands.command("shop", aliases=["store", "ショップ", "ストア"])
    async def fetch_today_shop(self, ctx: Context):
        def wrapper(view: discord.ui.View):
            async def select_account_region(interaction: Interaction):
                account: RiotAccount = self.bot.database.query(RiotAccount).filter(
                    RiotAccount.game_name == interaction.data["values"][0]).first()
                cl = new_valorant_client_api(account.region, account.username, account.password)
                try:
                    cl.activate()
                except Exception as e:
                    self.bot.logger.error(f"failed to login valorant client", exc_info=e)
                    await ctx.send(User.get_promised(self.bot.database, ctx.message.author.id).get_text(
                        "ログイン情報の更新が必要です。パスワードの変更などをした場合にこのメッセージが表示されます。「登録」コマンドを利用してください",
                        "You need to update your login credentials. This message will appear if you have changed your password. Please use the [register] command."))
                    view.stop()
                    return
                offers = cl.store_fetch_storefront()
                user = User.get_promised(self.bot.database, ctx.message.author.id)
                for offer_uuid in offers.get("SkinsPanelLayout", {}).get("SingleItemOffers", []):
                    skin = Weapon.get_promised(self.bot.database, offer_uuid, user)

                    embed = discord.Embed(title=skin.display_name, color=0xff0000,
                                          url=skin.streamed_video if skin.streamed_video else EmptyEmbed,
                                          description=user.get_text("↑から動画が見れます",
                                                                    "You can watch the video at↑") if skin.streamed_video else EmptyEmbed)
                    embed.set_author(name="valorant shop",
                                     icon_url="https://pbs.twimg.com/profile_images/1403218724681777152/rcOjWkLv_400x400.jpg")
                    embed.set_image(url=skin.display_icon)
                    await ctx.send(embed=embed)
                if offers.get("BonusStore") is not None:
                    await ctx.send(user.get_text("ナイトマーケットが開かれています！\n`nightmarket`, `ナイトストア`コマンドで確認しましょう！",
                                                 "The night market is open.！\nLet's check it with the command `nightmarket`, `ナイトストア`"))
                view.stop()

            return select_account_region

        await self.list_account_and_execute(ctx, wrapper)

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

    @commands.command("register", aliases=["登録"])
    async def register_riot_account(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)
        if ctx.message.author.dm_channel is None or ctx.channel.id != ctx.message.author.dm_channel.id:
            await ctx.send(user.get_text("ログイン情報の登録が必要です。\n個人チャットで登録を進めてください",
                                         "You need to register your login information. Please proceed to register in \n personal chat"))
        await self.register_riot_user_internal(ctx.message.author)

    async def register_riot_user_internal(self, to: Union[discord.Member, discord.User]):
        user = User.get_promised(self.bot.database, to.id)
        embed = discord.Embed(title="VALORANT AUTHENTICATION",
                              description=user.get_text("ショップのスキン情報を入手するためには、以下のValorantのアカウント情報が必要です。",
                                                        "The following Valorant account information is required in order to fetch the store skin information."),
                              color=0xff0000)
        embed.set_author(name="play valorant",
                         icon_url="https://pbs.twimg.com/profile_images/1403218724681777152/rcOjWkLv_400x400.jpg")
        embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/1403218724681777152/rcOjWkLv_400x400.jpg")
        embed.add_field(
            name=user.get_text("ユーザー名", "user id"),
            value=user.get_text("ゲームにログインするときに使用するIDです。", "The ID you use to log in to the game")
        )
        embed.add_field(
            name=user.get_text("パスワード", "password"),
            value=user.get_text("ゲームにログインするときに使用するパスワードです。", "The password you use to log in to the game.")
        )
        embed.set_footer(text=user.get_text(
            "ログイン情報はショップの内容を確認する目的のみに使用されます。",
            "Your login information will be used only for the purpose of checking the contents of the store."
        ))
        await to.send(embed=embed)
        await to.send(
            file=discord.File(user.get_text("assets/valorant_login_form_ja.png", "assets/valorant_login_form_en.png"))
        )

        def check_is_private_message(msg: discord.Message) -> bool:
            if msg.author.id != to.id:
                return False
            if msg.channel.id != to.dm_channel.id:
                return False
            return True

        riot_account = RiotAccount()
        view = discord.ui.View(timeout=240)
        menu = discord.ui.Select(options=[
            discord.SelectOption(
                label=region,
                description=description
            ) for region, description in {
                "ap": user.get_text("アジア太平洋地域(日本を含みます)", "Asia Pacific"),
                "na": user.get_text("北アメリカ", "North America"),
                "eu": user.get_text("ヨーロッパ", "Europe"),
                "latam": user.get_text("ラテンアメリカ", "Latin America"),
                "br": user.get_text("ブラジル", "Brazil"),
                "kr": user.get_text("韓国", "Korea"),
                "pbe": user.get_text("パブリックベータ環境", "Public Beta Environment")
            }.items()
        ])

        async def select_account_region(interaction: Interaction):
            riot_account.region = interaction.data["values"][0]
            view.stop()

        menu.callback = select_account_region
        view.add_item(menu)
        await to.send(content=user.get_text("まずはアカウントの地域を選択してください。\n正しいものを選択しないとログインできません。",
                                            "Select the region of your account\nIf you do not select the correct one, you will not be able to log in."),
                      view=view)

        view_stat = await view.wait()
        if view_stat:
            await to.send(user.get_text("４分以上応答がないため、登録のプロセスを終了します。",
                                        "Since there is no response for more than 4 minutes, the registration process is terminated."))

        await to.send(user.get_text("ユーザー名を送信してください。", "Submit your user id"))

        try:
            username = await self.bot.wait_for("message", check=check_is_private_message, timeout=240)
        except asyncio.TimeoutError:
            await to.send(user.get_text("４分以上応答がないため、登録のプロセスを終了します。",
                                        "Since there is no response for more than 4 minutes, the registration process is terminated."))
            return
        riot_account.username = username.content
        for account in user.riot_accounts:
            if account.username == riot_account.username:
                await to.send(
                    user.get_text("このユーザーIDはすでにあなたのアカウントに登録されています。\n削除する場合は[登録解除]コマンドを利用してください",
                                  "This user ID has already been registered in your account.\nTo delete, use the [unregister] command.")
                )
                return

        await to.send(user.get_text("次に、パスワードを送信してください。", "Submit your password"))
        try:
            password = await self.bot.wait_for("message", check=check_is_private_message, timeout=240)
        except asyncio.TimeoutError:
            await to.send(user.get_text("４分以上応答がないため、登録のプロセスを終了します。",
                                        "Since there is no response for more than 4 minutes, the registration process is terminated."))
            return
        riot_account.password = password.content

        cl = new_valorant_client_api(riot_account.region, riot_account.username, riot_account.password)
        try:
            cl.activate()
        except Exception as e:
            self.bot.logger.error(f"failed to login valorant client", exc_info=e)
            await to.send(user.get_text(
                "ログインの情報に誤りがあります。\n再度「登録」コマンドを利用してログイン情報を登録してください。",
                "Invalid credentials, Please use the [register] command again to register your login information."))
            return
        name = cl.fetch_player_name()
        riot_account.game_name = f"{name[0]['GameName']}#{name[0]['TagLine']}"
        user.riot_accounts.append(riot_account)
        self.bot.database.commit()
        await to.send(user.get_text(
            f"ログイン情報の入力が完了しました。\n{name[0]['GameName']}#{name[0]['TagLine']}",
            f"Your login information has been entered.\n{name[0]['GameName']}#{name[0]['TagLine']}"
        ))

    @commands.command("unregister", aliases=["登録解除"])
    async def unregister_riot_account(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)

        def wrapper(view: discord.ui.View):
            async def select_account_region(interaction: Interaction):
                account = self.bot.database.query(RiotAccount).filter(
                    RiotAccount.game_name == interaction.data["values"][0]).first()
                self.bot.database.delete(account)
                self.bot.database.commit()
                view.stop()
                await ctx.send(user.get_text("完了しました", "Done"))

            return select_account_region

        await self.list_account_and_execute(ctx, wrapper)


def setup(bot: ValorantStoreBot):
    bot.add_cog(CommandsHandler(bot))
