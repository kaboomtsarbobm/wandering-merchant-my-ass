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

from .models import TraderConfig, TraderItem
from .render import render_trader

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


CATCH_REWARD = 20


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
    def __init__(self, item: TraderItem, bot: "BallsDexBot"):
        super().__init__(
            label=f"{item_name(item)} - {format_currency(item.price, shortened=False, bot=bot)}"[:80],
            style=discord.ButtonStyle.green,
        )
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


class TraderView(discord.ui.View):
    def __init__(self, items: list[TraderItem], bot: "BallsDexBot", stay_seconds: int, leave_message: str):
        super().__init__(timeout=stay_seconds)
        self.message: discord.Message | None = None
        self.leave_message = leave_message
        for item in items:
            self.add_item(BuyButton(item, bot))

    async def on_timeout(self):
        if self.message is None:
            return
        embed = discord.Embed(description=self.leave_message, colour=discord.Colour.dark_grey())
        embed.set_image(url="attachment://trader.png")
        try:
            await self.message.edit(embed=embed, view=None)
        except discord.HTTPException:
            pass


class WanderingTrader(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.last_roll = time.monotonic()
        self.original_catch = BallSpawnView.catch_ball
        BallSpawnView.catch_ball = reward_catches(self.original_catch)
        self.roll_loop.start()

    async def cog_unload(self):
        BallSpawnView.catch_ball = self.original_catch
        self.roll_loop.cancel()

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
        picture: bytes | None,
    ):
        picks = random.sample(pool, min(3, len(pool)))
        lines = [
            (item_name(item), format_currency(item.price, shortened=False, bot=self.bot)) for item in picks
        ]
        buffer = await asyncio.to_thread(render_trader, lines, picture)
        embed = discord.Embed(description=config.spawn_message, colour=discord.Colour.gold())
        embed.set_image(url="attachment://trader.png")
        embed.set_footer(text=f"He leaves in {config.stay_minutes} minutes")
        view = TraderView(picks, self.bot, config.stay_minutes * 60, config.leave_message)
        try:
            view.message = await channel.send(
                embed=embed, file=discord.File(buffer, filename="trader.png"), view=view
            )
        except discord.HTTPException:
            return

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
        picture = await fetch_picture(config.image_url)
        guilds = GuildConfig.objects.filter(enabled=True, spawn_channel__isnull=False)
        async for guild_config in guilds:
            if random.randint(1, 100) > config.spawn_chance:
                continue
            channel = self.bot.get_channel(guild_config.spawn_channel)
            if not isinstance(channel, discord.TextChannel):
                continue
            await self.spawn(channel, config, pool, picture)

    @roll_loop.before_loop
    async def before_roll_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(WanderingTrader(bot))
