import asyncio
import datetime
import logging
import random
import time
from typing import TYPE_CHECKING

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from django.db.models import F, Q
from django.utils import timezone

from ballsdex.packages.countryballs.countryball import BallSpawnView
from bd_models.models import BallInstance, GuildConfig, Player
from settings.models import settings
from settings.utils import format_currency

from .models import (
    PlayerListing,
    PlayerMerchantSettings,
    PlayerMerchantTemplate,
    TraderConfig,
    TraderDialogue,
    TraderItem,
)
from .render import render_trader
from .token_cog import SpawnTokens
from .token_models import InstantMerchantConfig

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger(__name__)

CATCH_REWARD = 20
SCENE_IMAGE = "attachment://trader.png"

BUTTON_STYLES = {
    "green": discord.ButtonStyle.success,
    "blurple": discord.ButtonStyle.primary,
    "grey": discord.ButtonStyle.secondary,
    "red": discord.ButtonStyle.danger,
}


def reward_catches(original):
    async def catch_ball(self, user, *, player, guild):
        result = await original(self, user, player=player, guild=guild)
        await Player.objects.filter(pk=result[0].player_id).aupdate(money=F("money") + CATCH_REWARD)
        return result

    return catch_ball


def fill(text: str, **values: str) -> str:
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def ball_label(ball, special) -> str:
    if special:
        return f"{special.name} {ball.country}"
    return ball.country


def item_name(item: TraderItem) -> str:
    return ball_label(item.ball, item.special)


def pick_items(pool: list[TraderItem], count: int = 3) -> list[TraderItem]:
    if len(pool) <= count:
        return list(pool)
    remaining = list(pool)
    picks: list[TraderItem] = []
    while remaining and len(picks) < count:
        choice = random.choices(remaining, weights=[max(i.chance, 1) for i in remaining])[0]
        picks.append(choice)
        remaining.remove(choice)
    return picks


def parse_colour(value: str) -> discord.Colour:
    try:
        return discord.Colour(int(value.lstrip("#"), 16))
    except ValueError:
        return discord.Colour.gold()


def emoji_prefix(bot: "BallsDexBot", emoji_id: int | None) -> str:
    if not emoji_id:
        return ""
    emoji = bot.get_emoji(emoji_id)
    return f"{emoji} " if emoji else ""


async def fetch_picture(url: str) -> bytes | None:
    if not url:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                return await response.read()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None


async def fetch_scene(config) -> tuple[bytes | None, bytes | None, bytes | None]:
    picture, background, overlay = await asyncio.gather(
        fetch_picture(config.image_url),
        fetch_picture(config.background_url),
        fetch_picture(config.overlay_url),
    )
    return picture, background, overlay


class BuyButton(discord.ui.Button):
    def __init__(self, item: TraderItem, bot: "BallsDexBot", config: TraderConfig):
        label = config.button_label.replace("{name}", item_name(item)).replace(
            "{price}", format_currency(item.price, shortened=False, bot=bot)
        )
        super().__init__(label=label[:80], style=BUTTON_STYLES.get(config.button_style, discord.ButtonStyle.success))
        self.item = item
        self.bot = bot
        self.config = config
        self.trader: "TraderView | None" = None

    async def purchase(self, user: discord.abc.User) -> str | None:
        player, _ = await Player.objects.aget_or_create(discord_id=user.id)
        paid = await Player.objects.filter(pk=player.pk, money__gte=self.item.price).aupdate(
            money=F("money") - self.item.price
        )
        if not paid:
            return f"You don't have enough {settings.currency_display_plural(self.bot)}."
        await BallInstance.objects.acreate(
            ball=self.item.ball,
            player=player,
            special=self.item.special,
            attack_bonus=random.randint(-20, 20),
            health_bonus=random.randint(-20, 20),
        )
        text = fill(
            self.item.purchase_message or self.config.purchase_message,
            name=item_name(self.item),
            price=format_currency(self.item.price, bot=self.bot),
            user=user.mention,
        )
        image = self.item.purchase_image_url or self.config.purchase_image_url
        if self.trader is not None:
            self.trader.show_purchase(text, image)
        return None

    async def callback(self, interaction: discord.Interaction):
        if self.config.confirm_purchase:
            question = fill(
                self.config.confirm_message,
                name=item_name(self.item),
                price=format_currency(self.item.price, bot=self.bot),
                user=interaction.user.mention,
            )
            await interaction.response.send_message(question, view=ConfirmView(self), ephemeral=True)
            return
        await interaction.response.defer()
        error = await self.purchase(interaction.user)
        if error:
            await interaction.followup.send(error, ephemeral=True)
            return
        if self.trader is not None:
            await interaction.edit_original_response(view=self.trader)


class ConfirmView(discord.ui.View):
    def __init__(self, buy: BuyButton):
        super().__init__(timeout=60)
        self.buy = buy
        self.used = False
        config = buy.config
        yes = discord.ui.Button(
            label=config.confirm_yes_label[:80],
            style=BUTTON_STYLES.get(config.confirm_yes_style, discord.ButtonStyle.success),
        )
        no = discord.ui.Button(
            label=config.confirm_no_label[:80],
            style=BUTTON_STYLES.get(config.confirm_no_style, discord.ButtonStyle.danger),
        )
        yes.callback = self.confirm
        no.callback = self.cancel
        self.add_item(yes)
        self.add_item(no)

    async def confirm(self, interaction: discord.Interaction):
        if self.used:
            await interaction.response.defer()
            return
        self.used = True
        self.stop()
        await interaction.response.defer()
        trader = self.buy.trader
        if trader is None or trader.is_finished():
            await interaction.edit_original_response(content="The trader has already left.", view=None)
            return
        error = await self.buy.purchase(interaction.user)
        if error:
            await interaction.edit_original_response(content=error, view=None)
            return
        try:
            await trader.message.edit(view=trader)
        except discord.HTTPException:
            pass
        await interaction.delete_original_response()

    async def cancel(self, interaction: discord.Interaction):
        if self.used:
            await interaction.response.defer()
            return
        self.used = True
        self.stop()
        text = fill(
            self.buy.config.confirm_cancel_message,
            name=item_name(self.buy.item),
            price=format_currency(self.buy.item.price, bot=self.buy.bot),
        )
        await interaction.response.edit_message(content=text, view=None)


class TraderView(discord.ui.LayoutView):
    def __init__(self, bot: "BallsDexBot", config: TraderConfig, items: list[TraderItem], lines: list[str]):
        super().__init__(timeout=None)
        self.message: discord.Message | None = None
        self.lines = lines
        self.interval = max(config.dialogue_seconds, 3)
        self.stay_seconds = config.stay_minutes * 60
        self.prefix = emoji_prefix(bot, config.emoji_id)
        self.spawn_text = self.prefix + config.spawn_message
        self.leave_text = self.prefix + config.leave_message
        self.purchased = False
        self.hold_until = 0.0
        self.dialogue = discord.ui.TextDisplay(self.spawn_text)
        self.gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(SCENE_IMAGE))
        buttons = [BuyButton(item, bot, config) for item in items]
        for button in buttons:
            button.trader = self
        self.row = discord.ui.ActionRow(*buttons)
        self.timer = None
        children = []
        if config.title:
            children.append(discord.ui.TextDisplay(f"## {config.title}"))
        children.append(self.dialogue)
        children.append(self.gallery)
        if config.show_timer:
            self.timer = discord.ui.TextDisplay(f"-# Leaves <t:{int(time.time()) + self.stay_seconds}:R>")
            children.append(self.timer)
        children.append(self.row)
        self.container = discord.ui.Container(*children, accent_colour=parse_colour(config.accent_colour))
        self.add_item(self.container)

    def set_image(self, url: str):
        self.gallery.clear_items()
        self.gallery.append_item(discord.MediaGalleryItem(url or SCENE_IMAGE))

    def show_purchase(self, text: str, image: str):
        self.dialogue.content = self.prefix + text
        self.set_image(image)
        self.purchased = True
        self.hold_until = time.monotonic() + 8

    async def run(self):
        end = time.monotonic() + self.stay_seconds
        index = 0
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            await asyncio.sleep(min(self.interval, remaining))
            now = time.monotonic()
            if now >= end:
                break
            if now < self.hold_until:
                continue
            if self.purchased:
                self.purchased = False
                self.set_image(SCENE_IMAGE)
                self.dialogue.content = self.spawn_text
            elif self.lines:
                self.dialogue.content = self.lines[index % len(self.lines)]
                index += 1
            else:
                continue
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                self.stop()
                return
            except discord.HTTPException:
                pass
        await self.leave()

    async def leave(self):
        if self.purchased:
            self.purchased = False
            self.set_image(SCENE_IMAGE)
        self.dialogue.content = self.leave_text
        self.container.accent_colour = discord.Colour.dark_grey()
        self.container.remove_item(self.row)
        if self.timer is not None:
            self.container.remove_item(self.timer)
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass
        self.stop()


class WanderingTrader(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.last_roll: dict[int, float] = {}
        self.tasks: set[asyncio.Task] = set()
        self.original_catch = BallSpawnView.catch_ball
        BallSpawnView.catch_ball = reward_catches(self.original_catch)
        self.roll_loop.start()

    async def cog_unload(self):
        BallSpawnView.catch_ball = self.original_catch
        self.roll_loop.cancel()
        for task in self.tasks:
            task.cancel()

    async def get_config(self) -> TraderConfig:
        config = await TraderConfig.objects.order_by("pk").afirst()
        if config is None:
            config = await TraderConfig.objects.acreate()
        return config

    async def merchant_pool(self, config: TraderConfig) -> list[TraderItem]:
        default_pk = await TraderConfig.objects.order_by("pk").values_list("pk", flat=True).afirst()
        query = TraderItem.objects.filter(enabled=True, chance__gt=0)
        if config.pk == default_pk:
            query = query.filter(Q(merchant=config) | Q(merchant__isnull=True))
        else:
            query = query.filter(merchant=config)
        return [i async for i in query.select_related("ball", "special")]

    async def load_lines(self, config: TraderConfig) -> list[str]:
        default_pk = await TraderConfig.objects.order_by("pk").values_list("pk", flat=True).afirst()
        query = TraderDialogue.objects.filter(enabled=True)
        if config.pk == default_pk:
            query = query.filter(Q(merchant=config) | Q(merchant__isnull=True))
        else:
            query = query.filter(merchant=config)
        dialogue = [d async for d in query]
        return [emoji_prefix(self.bot, d.emoji_id or config.emoji_id) + d.text for d in dialogue]

    async def spawn(
        self,
        channel: discord.TextChannel,
        config: TraderConfig,
        pool: list[TraderItem],
        lines: list[str],
        images: tuple[bytes | None, bytes | None, bytes | None],
    ):
        picks = pick_items(pool)
        scene = [(item_name(item), format_currency(item.price, shortened=False, bot=self.bot)) for item in picks]
        buffer = await asyncio.to_thread(
            render_trader,
            scene,
            *images,
            font=config.item_font,
            size=config.item_font_size,
            colour=config.item_font_colour,
        )
        view = TraderView(self.bot, config, picks, lines)
        try:
            view.message = await channel.send(file=discord.File(buffer, filename="trader.png"), view=view)
        except discord.HTTPException:
            return
        task = asyncio.create_task(view.run())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    @app_commands.command(name="merchant", description="Spawn a wandering trader right now")
    @app_commands.describe(merchant="Which merchant to spawn, leave empty for the main one")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def merchant(self, interaction: discord.Interaction["BallsDexBot"], merchant: str | None = None):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("The trader can only show up in a text channel.", ephemeral=True)
            return

        use_instant = merchant is None
        if merchant is None:
            config = await self.get_config()
        else:
            config = await TraderConfig.objects.filter(pk=int(merchant)).afirst() if merchant.isdigit() else None
            if config is None:
                await interaction.followup.send("I couldn't find that merchant.", ephemeral=True)
                return

        picks: list[TraderItem] = []
        if use_instant:
            instant = await InstantMerchantConfig.objects.select_related(
                "item_1__ball", "item_1__special", "item_2__ball", "item_2__special", "item_3__ball", "item_3__special"
            ).afirst()
            if instant is not None:
                for item in (instant.item_1, instant.item_2, instant.item_3):
                    if item is not None and all(item.pk != p.pk for p in picks):
                        picks.append(item)

        if len(picks) < 3:
            pool = await self.merchant_pool(config)
            taken = {p.pk for p in picks}
            extras = [i for i in pool if i.pk not in taken]
            picks.extend(pick_items(extras, 3 - len(picks)))

        if not picks:
            await interaction.followup.send("There are no trader items set up yet.", ephemeral=True)
            return

        lines = await self.load_lines(config)
        images = await fetch_scene(config)
        # this doesn't touch the normal roll timers
        await self.spawn(channel, config, picks, lines, images)
        await interaction.followup.send("The trader has arrived.", ephemeral=True)

    @merchant.autocomplete("merchant")
    async def merchant_autocomplete(self, interaction: discord.Interaction, current: str):
        query = TraderConfig.objects.filter(title__icontains=current).order_by("pk")[:25]
        return [app_commands.Choice(name=(c.title or f"Merchant {c.pk}")[:100], value=str(c.pk)) async for c in query]

    @tasks.loop(seconds=30)
    async def roll_loop(self):
        configs = [c async for c in TraderConfig.objects.order_by("pk")]
        if not configs:
            await self.get_config()
            return
        now = time.monotonic()
        for config in configs:
            if not config.enabled:
                continue
            last = self.last_roll.setdefault(config.pk, now)
            if now - last < config.interval_minutes * 60:
                continue
            self.last_roll[config.pk] = now
            pool = await self.merchant_pool(config)
            if not pool:
                continue
            lines = await self.load_lines(config)
            images = await fetch_scene(config)
            guilds = GuildConfig.objects.filter(enabled=True, spawn_channel__isnull=False)
            async for guild_config in guilds:
                if random.randint(1, 100) > config.spawn_chance:
                    continue
                channel = self.bot.get_channel(guild_config.spawn_channel)
                if not isinstance(channel, discord.TextChannel):
                    continue
                await self.spawn(channel, config, pool, lines, images)

    @roll_loop.before_loop
    async def before_roll_loop(self):
        await self.bot.wait_until_ready()


class ListingBuyButton(discord.ui.Button):
    def __init__(self, label: str):
        super().__init__(label=label[:80], style=discord.ButtonStyle.success)
        self.listing_view: "ListingView | None" = None

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.listing_view is not None:
            await self.listing_view.buy(interaction)


class ListingView(discord.ui.LayoutView):
    def __init__(
        self,
        bot: "BallsDexBot",
        listing: PlayerListing,
        template: PlayerMerchantTemplate,
        name: str,
        seller_discord_id: int,
        stay_seconds: int,
    ):
        super().__init__(timeout=None)
        self.bot = bot
        self.listing = listing
        self.template = template
        self.name = name
        self.seller_discord_id = seller_discord_id
        self.stay_seconds = stay_seconds
        self.message: discord.Message | None = None
        self.closed = False
        self.price_text = format_currency(listing.price, shortened=False, bot=bot)
        self.values = {
            "seller": f"<@{seller_discord_id}>",
            "name": name,
            "price": self.price_text,
        }
        self.dialogue = discord.ui.TextDisplay(fill(template.spawn_message, **self.values))
        self.gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(SCENE_IMAGE))
        button = ListingBuyButton(f"Buy {name} - {self.price_text}")
        button.listing_view = self
        self.row = discord.ui.ActionRow(button)
        self.timer = discord.ui.TextDisplay(f"-# Leaves <t:{int(time.time()) + stay_seconds}:R>")
        children = []
        if template.name:
            children.append(discord.ui.TextDisplay(f"## {template.name}"))
        children.extend([self.dialogue, self.gallery, self.timer, self.row])
        self.container = discord.ui.Container(*children, accent_colour=parse_colour(template.accent_colour))
        self.add_item(self.container)

    def set_image(self, url: str):
        self.gallery.clear_items()
        self.gallery.append_item(discord.MediaGalleryItem(url or SCENE_IMAGE))

    def finish(self, text: str, image: str = "", colour: discord.Colour | None = None):
        self.closed = True
        self.dialogue.content = text
        self.set_image(image)
        if colour is not None:
            self.container.accent_colour = colour
        self.container.remove_item(self.row)
        self.container.remove_item(self.timer)

    async def buy(self, interaction: discord.Interaction):
        listing = self.listing
        if self.closed:
            await interaction.followup.send("This sale is already over.", ephemeral=True)
            return
        if interaction.user.id == self.seller_discord_id:
            await interaction.followup.send("You can't buy your own listing.", ephemeral=True)
            return

        buyer, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        claimed = await PlayerListing.objects.filter(pk=listing.pk, status="active").aupdate(
            status="sold", buyer=buyer
        )
        if not claimed:
            await interaction.followup.send("Someone else just bought this.", ephemeral=True)
            return

        paid = await Player.objects.filter(pk=buyer.pk, money__gte=listing.price).aupdate(
            money=F("money") - listing.price
        )
        if not paid:
            await PlayerListing.objects.filter(pk=listing.pk, status="sold").aupdate(status="active", buyer=None)
            await interaction.followup.send(
                f"You don't have enough {settings.currency_display_plural(self.bot)}.", ephemeral=True
            )
            return

        # the ball stays with the seller until now, so check they still own it
        filters = {"pk": listing.ball_instance_id, "player_id": listing.seller_id}
        if hasattr(BallInstance, "locked"):
            filters["locked__isnull"] = True
        moved = await BallInstance.objects.filter(**filters).aupdate(player=buyer)
        if not moved:
            await Player.objects.filter(pk=buyer.pk).aupdate(money=F("money") + listing.price)
            await PlayerListing.objects.filter(pk=listing.pk).aupdate(status="cancelled", buyer=None)
            self.finish(
                fill(self.template.leave_message, seller=self.values["seller"], name=self.name),
                colour=discord.Colour.dark_grey(),
            )
            await interaction.edit_original_response(view=self)
            await interaction.followup.send(
                "The seller doesn't have that countryball anymore, you weren't charged.", ephemeral=True
            )
            self.stop()
            return

        payout = listing.price - (listing.price * listing.fee_percent) // 100
        await Player.objects.filter(pk=listing.seller_id).aupdate(money=F("money") + payout)

        self.finish(
            fill(self.template.purchase_message, user=interaction.user.mention, **self.values),
            self.template.purchase_image_url,
        )
        await interaction.edit_original_response(view=self)
        self.stop()

    async def run(self):
        await asyncio.sleep(self.stay_seconds)
        if self.closed:
            return
        expired = await PlayerListing.objects.filter(pk=self.listing.pk, status="active").aupdate(status="expired")
        if not expired:
            return
        self.finish(
            fill(self.template.leave_message, seller=self.values["seller"], name=self.name),
            colour=discord.Colour.dark_grey(),
        )
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass
        self.stop()


class PlayerMerchants(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.tasks: set[asyncio.Task] = set()

    async def cog_load(self):
        try:
            # listings can't survive a restart because their buttons are gone
            await PlayerListing.objects.filter(status="active").aupdate(status="expired")
        except Exception:
            log.exception("Could not clean up old player listings")

    async def cog_unload(self):
        for task in self.tasks:
            task.cancel()

    @app_commands.command(name="sell", description="Put one of your countryballs up for sale")
    @app_commands.describe(ball="The countryball to sell", price="How much you want for it", style="Which merchant shows it")
    @app_commands.guild_only()
    async def sell(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        ball: str,
        price: int,
        style: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("You can only sell in a text channel.", ephemeral=True)
            return

        rules = await PlayerMerchantSettings.objects.afirst()
        if rules is None:
            rules = await PlayerMerchantSettings.objects.acreate()
        if not rules.enabled:
            await interaction.followup.send("Player merchants are turned off right now.", ephemeral=True)
            return
        if price < rules.min_price or price > rules.max_price:
            await interaction.followup.send(
                f"The price has to be between {format_currency(rules.min_price, bot=self.bot)} "
                f"and {format_currency(rules.max_price, bot=self.bot)}.",
                ephemeral=True,
            )
            return

        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        now = timezone.now()

        active = await PlayerListing.objects.filter(seller=player, status="active", expires_at__gt=now).acount()
        if active >= rules.max_listings:
            await interaction.followup.send(
                f"You can only have {rules.max_listings} listing(s) up at once.", ephemeral=True
            )
            return
        last = await PlayerListing.objects.filter(seller=player).order_by("-created_at").afirst()
        if last is not None:
            ready = last.created_at + datetime.timedelta(minutes=rules.cooldown_minutes)
            if ready > now:
                wait = int((ready - now).total_seconds() // 60) + 1
                await interaction.followup.send(f"You can list again in about {wait} minute(s).", ephemeral=True)
                return

        instance = None
        if ball.isdigit():
            instance = await BallInstance.objects.filter(pk=int(ball), player=player).select_related(
                "ball", "special"
            ).afirst()
        if instance is None:
            await interaction.followup.send("Pick one of your own countryballs from the list.", ephemeral=True)
            return
        if getattr(instance, "tradeable", True) is False:
            await interaction.followup.send("That countryball can't be sold.", ephemeral=True)
            return
        if getattr(instance, "locked", None) is not None:
            await interaction.followup.send("That countryball is locked in a trade right now.", ephemeral=True)
            return
        if await PlayerListing.objects.filter(ball_instance=instance, status="active", expires_at__gt=now).aexists():
            await interaction.followup.send("That countryball is already for sale.", ephemeral=True)
            return

        templates = [t async for t in PlayerMerchantTemplate.objects.filter(enabled=True)]
        if not templates:
            await interaction.followup.send("No merchant styles are set up yet, ask an admin.", ephemeral=True)
            return
        template = random.choice(templates)
        if style and style.isdigit():
            template = next((t for t in templates if t.pk == int(style)), template)

        listing = await PlayerListing.objects.acreate(
            seller=player,
            ball_instance=instance,
            template=template,
            price=price,
            fee_percent=rules.fee_percent,
            expires_at=now + datetime.timedelta(minutes=rules.stay_minutes),
        )

        name = ball_label(instance.ball, instance.special)
        price_text = format_currency(price, shortened=False, bot=self.bot)
        images = await fetch_scene(template)
        buffer = await asyncio.to_thread(
            render_trader,
            [(name, price_text)],
            *images,
            font=template.item_font,
            size=template.item_font_size,
            colour=template.item_font_colour,
        )
        view = ListingView(self.bot, listing, template, name, interaction.user.id, rules.stay_minutes * 60)
        try:
            view.message = await channel.send(
                file=discord.File(buffer, filename="trader.png"),
                view=view,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            await PlayerListing.objects.filter(pk=listing.pk).adelete()
            await interaction.followup.send("I couldn't post in this channel.", ephemeral=True)
            return

        task = asyncio.create_task(view.run())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        await interaction.followup.send("Your listing is up. The countryball stays yours until someone buys it.", ephemeral=True)

    @sell.autocomplete("ball")
    async def ball_autocomplete(self, interaction: discord.Interaction, current: str):
        query = BallInstance.objects.filter(player__discord_id=interaction.user.id).select_related("ball", "special")
        if current:
            query = query.filter(ball__country__icontains=current)
        results = []
        async for inst in query.order_by("-pk")[:25]:
            label = f"#{inst.pk:X} {ball_label(inst.ball, inst.special)} {inst.attack_bonus:+}%/{inst.health_bonus:+}%"
            results.append(app_commands.Choice(name=label[:100], value=str(inst.pk)))
        return results

    @sell.autocomplete("style")
    async def style_autocomplete(self, interaction: discord.Interaction, current: str):
        query = PlayerMerchantTemplate.objects.filter(enabled=True, name__icontains=current).order_by("name")[:25]
        return [app_commands.Choice(name=t.name[:100], value=str(t.pk)) async for t in query]


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(WanderingTrader(bot))
    await bot.add_cog(SpawnTokens(bot))
    await bot.add_cog(PlayerMerchants(bot))
