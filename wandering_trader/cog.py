import asyncio
import random
import time
from typing import TYPE_CHECKING

import aiohttp
import discord
from discord.ext import commands, tasks
from django.db.models import F

from ballsdex.packages.countryballs.countryball import BallSpawnView
from bd_models.models import BallInstance, GuildConfig, Player
from settings.models import settings
from settings.utils import format_currency

from .models import TraderConfig, TraderDialogue, TraderItem
from .render import render_trader

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


CATCH_REWARD = 20

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


def item_name(item: TraderItem) -> str:
    if item.special:
        return f"{item.special.name} {item.ball.country}"
    return item.ball.country


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


class BuyButton(discord.ui.Button):
    def __init__(self, item: TraderItem, bot: "BallsDexBot", config: TraderConfig):
        label = config.button_label.replace("{name}", item_name(item)).replace(
            "{price}", format_currency(item.price, shortened=False, bot=bot)
        )
        super().__init__(label=label[:80], style=BUTTON_STYLES.get(config.button_style, discord.ButtonStyle.success))
        self.item = item
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        paid = await Player.objects.filter(pk=player.pk, money__gte=self.item.price).aupdate(
            money=F("money") - self.item.price
        )
        if not paid:
            await interaction.followup.send(
                f"You don't have enough {settings.currency_display_plural(self.bot)}.", ephemeral=True
            )
            return
        await BallInstance.objects.acreate(
            ball=self.item.ball,
            player=player,
            special=self.item.special,
            attack_bonus=random.randint(-20, 20),
            health_bonus=random.randint(-20, 20),
        )
        await interaction.followup.send(
            f"You bought **{item_name(self.item)}** for {format_currency(self.item.price, bot=self.bot)}!",
            ephemeral=True,
        )


class TraderView(discord.ui.LayoutView):
    def __init__(self, bot: "BallsDexBot", config: TraderConfig, items: list[TraderItem], lines: list[str]):
        super().__init__(timeout=None)
        self.message: discord.Message | None = None
        self.lines = lines
        self.interval = max(config.dialogue_seconds, 3)
        self.stay_seconds = config.stay_minutes * 60
        prefix = emoji_prefix(bot, config.emoji_id)
        self.leave_text = prefix + config.leave_message
        self.dialogue = discord.ui.TextDisplay(prefix + config.spawn_message)
        self.row = discord.ui.ActionRow(*(BuyButton(item, bot, config) for item in items))
        self.timer = None
        children = []
        if config.title:
            children.append(discord.ui.TextDisplay(f"## {config.title}"))
        children.append(self.dialogue)
        children.append(discord.ui.MediaGallery(discord.MediaGalleryItem("attachment://trader.png")))
        if config.show_timer:
            self.timer = discord.ui.TextDisplay(f"-# Leaves <t:{int(time.time()) + self.stay_seconds}:R>")
            children.append(self.timer)
        children.append(self.row)
        self.container = discord.ui.Container(*children, accent_colour=parse_colour(config.accent_colour))
        self.add_item(self.container)

    async def run(self):
        end = time.monotonic() + self.stay_seconds
        index = 0
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            if not self.lines:
                await asyncio.sleep(remaining)
                break
            await asyncio.sleep(min(self.interval, remaining))
            if time.monotonic() >= end:
                break
            self.dialogue.content = self.lines[index % len(self.lines)]
            index += 1
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                self.stop()
                return
            except discord.HTTPException:
                pass
        await self.leave()

    async def leave(self):
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
        self.last_roll = time.monotonic()
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
        config = await TraderConfig.objects.afirst()
        if config is None:
            config = await TraderConfig.objects.acreate()
        return config

    async def spawn(
        self,
        channel: discord.TextChannel,
        config: TraderConfig,
        pool: list[TraderItem],
        lines: list[str],
        picture: bytes | None,
    ):
        picks = random.sample(pool, min(3, len(pool)))
        scene = [(item_name(item), format_currency(item.price, shortened=False, bot=self.bot)) for item in picks]
        buffer = await asyncio.to_thread(render_trader, scene, picture)
        view = TraderView(self.bot, config, picks, lines)
        try:
            view.message = await channel.send(file=discord.File(buffer, filename="trader.png"), view=view)
        except discord.HTTPException:
            return
        task = asyncio.create_task(view.run())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    @tasks.loop(seconds=30)
    async def roll_loop(self):
        config = await self.get_config()
        if not config.enabled:
            return
        if time.monotonic() - self.last_roll < config.interval_minutes * 60:
            return
        self.last_roll = time.monotonic()
        pool = [i async for i in TraderItem.objects.filter(enabled=True).select_related("ball", "special")]
        if not pool:
            return
        dialogue = [d async for d in TraderDialogue.objects.filter(enabled=True)]
        lines = [emoji_prefix(self.bot, d.emoji_id or config.emoji_id) + d.text for d in dialogue]
        picture = await fetch_picture(config.image_url)
        guilds = GuildConfig.objects.filter(enabled=True, spawn_channel__isnull=False)
        async for guild_config in guilds:
            if random.randint(1, 100) > config.spawn_chance:
                continue
            channel = self.bot.get_channel(guild_config.spawn_channel)
            if not isinstance(channel, discord.TextChannel):
                continue
            await self.spawn(channel, config, pool, lines, picture)

    @roll_loop.before_loop
    async def before_roll_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(WanderingTrader(bot))
