import asyncio
import random
from datetime import timedelta, datetime
from typing import Union, Callable

import discord
import pytz
from discord import Interaction
from discord.embeds import EmptyEmbed
from discord.ext import commands
from discord.ext.commands import Context

from client import ValorantStoreBot
from database import User, Weapon, Guild
from database.user import RiotAccount


class CommandsHandler(commands.Cog):
    def __init__(self, bot: ValorantStoreBot):
        self.bot = bot

    async def list_account_and_execute(self, ctx: Context, func: Callable):
        user = User.get_promised(self.bot.database, ctx.message.author.id)

        view = discord.ui.View(timeout=240)
        accounts = user.riot_accounts
        if len(accounts) == 0:
            await ctx.send(user.get_text("アカウント情報が登録されていません\n[登録]コマンドを利用して登録してください",
                                         "Your account information has not been registered yet \nAdd your account information using the [register] command."))
            return
        if len(accounts) == 1:
            async def interaction_handler(*args, **kwargs):
                content = kwargs.get("content")
                if content is not None:
                    await ctx.send(content=kwargs.get("content"))

            await func(view)(type("Interaction", (object,), {
                "data": {"values": [accounts[0].game_name]},
                "user": type("User", (object,), {"id": ctx.message.author.id}),
                "response": type("InteractionResponse", (object,), {"send_message": interaction_handler})
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
        await view.wait()

    @commands.command("autosend")
    async def setup_auto_send(self, ctx: Context):

        def wrapper(view: discord.ui.View):
            async def select_auto_send_time(interaction: Interaction):
                await interaction.response.send_message(content="processing request....")
                account: RiotAccount = self.bot.database.query(RiotAccount).filter(
                    RiotAccount.game_name == interaction.data["values"][0]).first()
                user = User.get_promised(self.bot.database, ctx.message.author.id)
                if not user.is_premium:
                    await ctx.send(user.get_text("この機能はプレミアムユーザー限定です。\n詳細は「プレミアム」コマンドを参照してください",
                                                 "This feature is only available to Premium users.\ntype [premium] commands for details"))
                    view.stop()
                    return

                def message_check(msg: discord.Message):
                    if msg.channel.id != ctx.channel.id:
                        return False
                    if msg.author.id != ctx.message.author.id:
                        return False
                    return True

                await ctx.send(user.get_text(
                    "https://ja.wikipedia.org/wiki/ISO_3166-1\nこの一覧から、住んでいる国のうちAlpha-2の２文字のアルファベットをコピーして送信してください。日本はJPです。",
                    "https://wikipedia.org/wiki/ISO_3166-1\nFrom this list, please copy the two letters of the Alpha-2 alphabet from the country you live in and send it to us. Japan is JP."))
                try:
                    iso = await self.bot.wait_for("message", check=message_check, timeout=240)
                except asyncio.TimeoutError:
                    view.stop()
                    return
                try:
                    timezone = pytz.country_timezones(iso.content)[0]
                except (KeyError, IndexError):
                    await ctx.send(user.get_text("国コードが見つかりませんでした。\n再度「autosend」コマンドをお試しください。",
                                                 "The country code was not found. \nPlease try the [autosend] command again."))
                    view.stop()
                    return
                await ctx.send(user.get_text("何時にストアの内容を送信すればよろしいですか？1~24の間で答えてください。",
                                             "What time should I send the contents of your store?\nPlease answer between 1 and 24."))

                def message_check_hour(msg: discord.Message):
                    if msg.channel.id != ctx.channel.id:
                        return False
                    if msg.author.id != ctx.message.author.id:
                        return False
                    try:
                        min = int(msg.content)
                    except ValueError:
                        return False
                    if 1 <= min <= 24:
                        return True
                    return False

                try:
                    time = await self.bot.wait_for("message", check=message_check_hour, timeout=240)
                except asyncio.TimeoutError:
                    view.stop()
                    return

                user.auto_notify_at = int(time.content)
                user.auto_notify_timezone = timezone
                user.auto_notify_account = account
                self.bot.database.commit()
                view.stop()
                print(user.auto_notify_account.game_name)
                await ctx.send(user.get_text(
                    f"時刻を{timezone}の{time.content}時に設定しました。\n現在時刻は{datetime.now().astimezone(pytz.timezone(timezone))}です。",
                    f"set the time to {time.content} hour in {timezone}.\nThe current time is {datetime.now().astimezone(pytz.timezone(timezone))}."))
            return select_auto_send_time

        await self.list_account_and_execute(ctx, wrapper)

    @commands.command("gopremium")
    async def make_target_premium(self, ctx: Context):
        if ctx.message.author.id not in self.bot.admins:
            return
        mentioned_ids = [user.id for user in ctx.message.mentions]
        for user_id in mentioned_ids:
            user = User.get_promised(self.bot.database, user_id)
            user.is_premium = True
        self.bot.database.commit()
        await ctx.send(f"Congratulations! now a premium user: {len(mentioned_ids)}")

    @commands.command("onlyhere")
    @commands.has_permissions(administrator=True)
    async def response_only_this_channel(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)
        guild = Guild.get_promised(self.bot.database, ctx.guild.id)
        guild.response_here = ctx.channel.id
        self.bot.database.commit()
        await ctx.send(user.get_text(f"<#{guild.response_here}> のみでBOTがshopコマンドに反応するように設定しました。[everywhere]コマンドで解除できます",
                                     f"<#{guild.response_here}> only set the BOT to respond to the shop command.\nThis can be deactivated with the [everywhere] command"))

    @commands.command("everywhere")
    @commands.has_permissions(administrator=True)
    async def response_only_this_channel(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)
        guild = Guild.get_promised(self.bot.database, ctx.guild.id)
        guild.response_here = ""
        self.bot.database.commit()
        await ctx.send(user.get_text(f"すべての場所でBOTがshopコマンドに反応するように設定しました。",
                                     "All locations have been set up so that the BOT responds to shop commands."))

    @commands.command("rank")
    async def get_account_rank(self, ctx: Context):

        def wrapper(view: discord.ui.View):
            async def select_account_region(interaction: Interaction):
                await interaction.response.send_message(content="processing request....")
                account: RiotAccount = self.bot.database.query(RiotAccount).filter(
                    RiotAccount.game_name == interaction.data["values"][0]).first()
                user = User.get_promised(self.bot.database, ctx.message.author.id)
                cl = self.bot.new_valorant_client_api(user.is_premium, account)
                try:
                    await self.bot.run_blocking_func(cl.activate)
                except Exception as e:
                    self.bot.logger.error(f"failed to login valorant client", exc_info=e)
                    await ctx.send(user.get_text(
                        "ログイン情報の更新が必要です。パスワードの変更などをした場合にこのメッセージが表示されます。「登録」コマンドを利用してください。\nなお、まれにサーバーエラーにより実行できない場合があります。その場合はしばらくお待ちの上、再度お試しください",
                        "You need to update your login credentials. This message will appear if you have changed your password. Please use the [register] command.\nIn rare cases, it may not be possible to run the program due to a server error. In that case, please wait for a while and try again."))
                    view.stop()
                    return
                await ctx.send(self.bot.get_valorant_rank_tier(cl))

            return select_account_region

        await self.list_account_and_execute(ctx, wrapper)

    @commands.command("list")
    async def list_accounts(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)
        if len(user.riot_accounts) == 0:
            await ctx.send(user.get_text("アカウント情報が登録されていません\n[登録]コマンドを利用して登録してください",
                                         "Your account information has not been registered yet \nAdd your account information using the [register] command."))
            return
        await ctx.send("\n".join([account.game_name for account in user.riot_accounts]))

    @commands.command("update", aliases=["登録更新"])
    async def update_account(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)
        if not isinstance(ctx.message.channel, discord.channel.DMChannel) or ctx.message.author == self.bot.user:
            await ctx.send(user.get_text("この動作は個人チャットでする必要があります。", "This action needs to be done in private chat"))
            return
        if len(user.riot_accounts) == 0:
            await ctx.send(user.get_text("アカウント情報が登録されていません\n[登録]コマンドを利用して登録してください",
                                         "Your account information has not been registered yet \nAdd your account information using the [register] command."))
            return
        await self.unregister_riot_account(ctx)
        await self.register_riot_user_internal(ctx.message.author)

    async def _execute_shop_command_on_allowed_channel(self, ctx: Context, wrapper: Callable):
        if isinstance(ctx.message.channel, discord.channel.DMChannel) and ctx.message.author != self.bot.user:
            await self.list_account_and_execute(ctx, wrapper)
            return

        guild = Guild.get_promised(self.bot.database, ctx.guild.id)
        if guild.response_here != "" and ctx.channel.id != guild.response_here:
            return
        await self.list_account_and_execute(ctx, wrapper)

    @commands.command("nightmarket", aliases=["ナイトストア"])
    async def fetch_night_market(self, ctx: Context):
        def wrapper(view: discord.ui.View):
            async def select_account_region(interaction: Interaction):
                await interaction.response.send_message(content="processing request....")
                account: RiotAccount = self.bot.database.query(RiotAccount).filter(
                    RiotAccount.game_name == interaction.data["values"][0]).first()
                user = User.get_promised(self.bot.database, interaction.user.id)
                get_span = 20 if user.is_premium else 360
                if account.last_get_night_shops_at and account.last_get_night_shops_at + timedelta(
                        minutes=get_span) >= datetime.now():
                    await ctx.send(user.get_text(f"最後に取得してから{get_span}分経過していません。{get_span}分に一度のみこのコマンドを実行可能です。",
                                                 f"It has not been {get_span} minutes since the last acquisition. this command can only be executed once every {get_span} minutes."))
                    return
                account.last_get_night_shops_at = datetime.now()
                self.bot.database.commit()
                cl = self.bot.new_valorant_client_api(user.is_premium, account)
                try:
                    await self.bot.run_blocking_func(cl.activate)
                except Exception as e:
                    self.bot.logger.error(f"failed to login valorant client", exc_info=e)
                    await ctx.send(user.get_text(
                        "ログイン情報の更新が必要です。パスワードの変更などをした場合にこのメッセージが表示されます。「登録」コマンドを利用してください。\nなお、まれにサーバーエラーにより実行できない場合があります。その場合はしばらくお待ちの上、再度お試しください",
                        "You need to update your login credentials. This message will appear if you have changed your password. Please use the [register] command.\nIn rare cases, it may not be possible to run the program due to a server error. In that case, please wait for a while and try again."))
                    account.last_get_night_shops_at = None
                    self.bot.database.commit()
                    view.stop()
                    return
                user = User.get_promised(self.bot.database, ctx.message.author.id)
                offers = cl.store_fetch_storefront()
                if len(offers.get("BonusStore", {})) == 0:
                    await ctx.send(user.get_text(
                        "ショップの内容が見つかりませんでした。Valorantがメンテナンス中もしくは何かの障害の可能性があります。\nそのどちらでもない場合は開発者までご連絡ください。\nhttp://valorant.sakura.rip",
                        "The contents of the store could not be found, Valorant may be under maintenance or there may be some kind of fault. \nIf it is neither of those, please contact the developer.: \nhttp://valorant.sakura.rip"))

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

        await self._execute_shop_command_on_allowed_channel(ctx, wrapper)

    @commands.command("shop", aliases=["store", "ショップ", "ストア"])
    async def fetch_today_shop(self, ctx: Context):
        def wrapper(view: discord.ui.View):
            async def select_account_region(interaction: Interaction):
                await interaction.response.send_message(content="processing request....")
                account: RiotAccount = self.bot.database.query(RiotAccount).filter(
                    RiotAccount.game_name == interaction.data["values"][0]).first()
                user = User.get_promised(self.bot.database, interaction.user.id)
                get_span = 10 if user.is_premium else 180
                if account.last_get_shops_at and account.last_get_shops_at + timedelta(
                        minutes=get_span) >= datetime.now():
                    await ctx.send(user.get_text(f"最後に取得してから{get_span}分経過していません。{get_span}分に一度のみこのコマンドを実行可能です。",
                                                 f"It has not been {get_span} minutes since the last acquisition. this command can only be executed once every {get_span} minutes."))
                    return

                account.last_get_shops_at = datetime.now()
                self.bot.database.commit()
                cl = self.bot.new_valorant_client_api(user.is_premium, account)
                try:
                    await self.bot.run_blocking_func(cl.activate)
                except Exception as e:
                    self.bot.logger.error(f"failed to login valorant client", exc_info=e)
                    await ctx.send(User.get_promised(self.bot.database, ctx.message.author.id).get_text(
                        "ログイン情報の更新が必要です。パスワードの変更などをした場合にこのメッセージが表示されます。「登録」コマンドを利用してください。\nなお、まれにサーバーエラーにより実行できない場合があります。その場合はしばらくお待ちの上、再度お試しください",
                        "You need to update your login credentials. This message will appear if you have changed your password. Please use the [register] command.\nIn rare cases, it may not be possible to run the program due to a server error. In that case, please wait for a while and try again."))
                    account.last_get_shops_at = None
                    self.bot.database.commit()
                    view.stop()
                    return
                offers = cl.store_fetch_storefront()
                user = User.get_promised(self.bot.database, ctx.message.author.id)
                if len(offers.get("SkinsPanelLayout", {}).get("SingleItemOffers", [])) == 0:
                    await ctx.send(user.get_text(
                        "ショップの内容が見つかりませんでした。Valorantがメンテナンス中もしくは何かの障害の可能性があります。\nそのどちらでもない場合は開発者までご連絡ください。\nhttp://valorant.sakura.rip",
                        "The contents of the store could not be found, Valorant may be under maintenance or there may be some kind of fault. \nIf it is neither of those, please contact the developer.: \nhttp://valorant.sakura.rip"))

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

        await self._execute_shop_command_on_allowed_channel(ctx, wrapper)

    @commands.command("randommap", aliases=["ランダムマップ"])
    async def random_map(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)
        if user.language == "ja-JP":
            maps = ["アセント", "スプリット", "バインド", "ブリーズ", "アイスボックス", "ヘイブン", "フラクチャー"]
        else:
            maps = ["Icebox", "Breeze", "Ascent", "Haven", "Split", "Bind", "Fracture"]
        await ctx.send(random.choice(maps))

    @commands.command("language", aliases=["lang", "言語"])
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

    @commands.command("premium", aliases=["プレミアム"])
    async def get_premium_details(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)
        embed = discord.Embed(title=user.get_text("プレミアムユーザーの詳細", "Premium User Details"),
                              description=user.get_text(
                                  "Valorant store botの利用者は、プレミアムユーザーになることで以下の特典を得ることができます($5 払いきり, paypay/linepay/paypal/btc/ltc)",
                                  "Users of the Valorant store bot can get the following benefits by becoming a premium user($5 life time, paypal/btc/ltc)"),
                              color=0x800000)
        embed.set_author(name="valorant store bot", url="http://valorant.sakura.rip",
                         icon_url="https://pbs.twimg.com/profile_images/1403218724681777152/rcOjWkLv_400x400.jpg")
        embed.add_field(name=user.get_text("〇登録アカウント上限の解放", "〇Release of the maximum number of registered accounts"),
                        value=user.get_text("１アカウントの登録上限が10アカウントまで登録できるようになります",
                                            "The registration limit for one account will be increased to 10 accounts."),
                        inline=False)
        embed.add_field(name=user.get_text("〇取得制限時間の短縮", "〇Reduction of acquisition time limit"),
                        value=user.get_text("通常では3時間の制限が10分になります", "The normal three-hour limit will be 10 minutes."),
                        inline=False)
        embed.add_field(name=user.get_text("〇ユーザー体験の向上", "〇Improving the user experience"),
                        value=user.get_text(
                            "これまで、登録情報の更新が必要などのエラーメッセージが表示されることがありましたが、それぞれのアカウントに個別のプロキシを利用することでそれの出る確率が下がります。(このエラーはプロキシの数に対してユーザー数が多すぎたことが原因でした",
                            "It used to show error messages such as registration information needs to be updated, but by using a separate proxy for each account, the probability of that appearing is reduced. (This error was caused by the number of users being too large for the number of proxies."),
                        inline=False)
        embed.add_field(
            name=user.get_text("〇指定した時間にストア内容を自動送信", "〇Automatically send the store contents at the specified time."),
            value=user.get_text("毎朝8時等、指定した時間に今日のストアの内容が自動で送られます",
                                "The contents of today's store will be automatically sent to you at the time you specify, such as 8:00 a.m. every morning."),
            inline=False)
        embed.add_field(name=user.get_text("〇その他機能への早期アクセス", "〇Early access to other functions"),
                        value=user.get_text("開発中の機能などへの早期アクセスが可能です",
                                            "Early access to features under development, etc."), inline=False)
        embed.set_footer(text=user.get_text("お問い合わせは、Twitter ID @ch31212yのDMまでお願いします。",
                                            "For inquiries, please DM us at Twitter ID @ch31212y."))
        await ctx.send(embed=embed)
        if user.is_premium:
            await ctx.send(user.get_text("おめでとうございます！。あなたはプレミアムユーザーです", "Congratulations! You are a premium user!"))

    @commands.command("register", aliases=["登録"])
    async def register_riot_account(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)
        if not isinstance(ctx.message.channel, discord.channel.DMChannel) or ctx.message.author == self.bot.user:
            await ctx.send(user.get_text("ログイン情報の登録が必要です。\n個人チャットで登録を進めてください",
                                         "You need to register your login information. Please proceed to register in \n personal chat"))
        if user.is_premium:
            if len(user.riot_accounts) > 10:
                await ctx.send(user.get_text("登録可能なアカウント数上限は１０です。",
                                             "The maximum number of accounts that can be registered is 10."))
                return
        else:
            if len(user.riot_accounts) >= 1:
                await ctx.send(user.get_text("""すでに1アカウントの情報が登録されています。
複数アカウントの登録はプレミアムユーザーのみ可能です。
既に登録済みのアカウント情報を更新したい場合は「登録更新」コマンドを利用してください
プレミアムユーザーの詳細は`premium`, `プレミアム`コマンドを利用してください""", """One account has already been registered.
Multiple accounts can be registered only by premium users.
If you want to update the information of an already registered account, please use the `update` command
Use the `premium` or `プレミアム` commands to get the details of premium users
"""))
                return

        await self.register_riot_user_internal(ctx.message.author)

    async def register_riot_user_internal(self, to: Union[discord.Member, discord.User]):
        user = User.get_promised(self.bot.database, to.id)

        if user.try_activate_count >= 3:
            if user.activation_locked_at + timedelta(minutes=10) < datetime.now():
                user.try_activate_count = 0
                user.activation_locked_at = None
            else:
                await to.send(user.get_text(f"ログインの試行回数上限に達しました。({user.try_activate_count}回)\n10分後に再度お試しください。",
                                            f"The maximum number of login attempts has been reached. ({user.try_activate_count} times)\nplease try again 10 minutes later,."))
                return

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
            return
        await to.send(user.get_text("ユーザー名を送信してください。", "Submit your user id"))

        try:
            username = await self.bot.wait_for("message", check=check_is_private_message, timeout=240)
        except asyncio.TimeoutError:
            return
        riot_account.username = username.content
        for account in user.riot_accounts:
            if account.username == riot_account.username:
                await to.send(
                    user.get_text("このユーザーIDはすでにあなたのアカウントに登録されています。\n削除/再登録する場合は[登録解除]コマンドを利用してください",
                                  "This user ID has already been registered in your account.\nTo delete/reregister, use the [unregister] command.")
                )
                return

        await to.send(user.get_text("次に、パスワードを送信してください。", "Submit your password"))
        try:
            password = await self.bot.wait_for("message", check=check_is_private_message, timeout=240)
        except asyncio.TimeoutError:
            return
        riot_account.password = password.content
        await to.send(user.get_text("確認中です...", "checking...."))
        user.try_activate_count += 1
        cl = self.bot.new_valorant_client_api(user.is_premium, riot_account)
        try:
            await self.bot.run_blocking_func(cl.activate)
        except Exception as e:
            self.bot.logger.error(f"failed to login valorant client", exc_info=e)
            if user.try_activate_count >= 3:
                user.activation_locked_at = datetime.now()
                await to.send(user.get_text(f"ログインの試行回数上限に達しました。({user.try_activate_count}回)\n10分後に再度お試しください。",
                                            f"The maximum number of login attempts has been reached. ({user.try_activate_count} times)\nplease try again 10 minutes later,."))
                self.bot.database.commit()
                return
            await to.send(user.get_text(
                "ログインの情報に誤りがあります。\n再度「登録」コマンドを利用してログイン情報を登録してください。",
                "Invalid credentials, Please use the [register] command again to register your login information."))
            return
        user.try_activate_count = 0
        user.activation_locked_at = None
        name = cl.fetch_player_name()
        riot_account.game_name = f"{name[0]['GameName']}#{name[0]['TagLine']}"
        riot_account.puuid = cl.puuid
        user.riot_accounts.append(riot_account)
        self.bot.database.commit()
        await to.send(user.get_text(
            f"ログイン情報の入力が完了しました。\n{name[0]['GameName']}#{name[0]['TagLine']}\nRANK: {self.bot.get_valorant_rank_tier(cl)}",
            f"Your login information has been entered.\n{name[0]['GameName']}#{name[0]['TagLine']}\nRANK: {self.bot.get_valorant_rank_tier(cl)}"
        ))

    @commands.command("unregister", aliases=["登録解除"])
    async def unregister_riot_account(self, ctx: Context):
        user = User.get_promised(self.bot.database, ctx.message.author.id)

        if not isinstance(ctx.message.channel, discord.channel.DMChannel) or ctx.message.author == self.bot.user:
            await ctx.send(user.get_text("この動作は個人チャットでする必要があります。", "This action needs to be done in private chat"))
            return

        def wrapper(view: discord.ui.View):
            async def select_account_region(interaction: Interaction):
                await interaction.response.send_message(content="processing request....")
                account = self.bot.database.query(RiotAccount).filter(
                    RiotAccount.game_name == interaction.data["values"][0]).first()
                self.bot.database.delete(account)
                self.bot.database.commit()
                view.stop()
                await ctx.send(user.get_text(f"{account.username}: 完了しました", f"{account.username}: Done"))

            return select_account_region

        await self.list_account_and_execute(ctx, wrapper)


def setup(bot: ValorantStoreBot):
    bot.add_cog(CommandsHandler(bot))
