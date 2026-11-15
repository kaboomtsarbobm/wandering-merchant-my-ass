import random
import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from django.db.models import F

from bd_models.models import BallInstance, GuildConfig, Player

from .models import TraderConfig, TraderItem

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


def item_name(item: TraderItem) -> str:
    if item.special:
        return f"{item.special.name} {item.ball.country}"
    return item.ball.country


class BuyButton(discord.ui.Button):
    def __init__(self, item: TraderItem, currency: str):
        super().__init__(
            label=f"{item_name(item)} - {item.price:,} {currency}"[:80],
            style=discord.ButtonStyle.green,
        )
        self.item = item
        self.currency = currency

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        paid = await Player.objects.filter(pk=player.pk, money__gte=self.item.price).aupdate(
            money=F("money") - self.item.price
        )
        if not paid:
            await interaction.followup.send(f"You don't have enough {self.currency}.", ephemeral=True)
            return
        await BallInstance.objects.acreate(
            ball=self.item.ball,
            player=player,
            special=self.item.special,
            attack_bonus=random.randint(-20, 20),
            health_bonus=random.randint(-20, 20),
        )
        await interaction.followup.send(
            f"You bought **{item_name(self.item)}** for {self.item.price:,} {self.currency}!",
            ephemeral=True,
        )


class TraderView(discord.ui.View):
    def __init__(self, items: list[TraderItem], currency: str, stay_seconds: int, leave_message: str, image_url: str):
        super().__init__(timeout=stay_seconds)
        self.message: discord.Message | None = None
        self.leave_message = leave_message
        self.image_url = image_url
        for item in items:
            self.add_item(BuyButton(item, currency))

    async def on_timeout(self):
        if self.message is None:
            return
        embed = discord.Embed(description=self.leave_message, colour=discord.Colour.dark_grey())
        if self.image_url:
            embed.set_image(url=self.image_url)
        try:
            await self.message.edit(embed=embed, view=None)
        except discord.HTTPException:
            pass


class WanderingTrader(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.last_roll = time.monotonic()
        self.roll_loop.start()

    async def cog_unload(self):
        self.roll_loop.cancel()

    async def get_config(self) -> TraderConfig:
        config = await TraderConfig.objects.afirst()
        if config is None:
            config = await TraderConfig.objects.acreate()
        return config

    async def spawn(self, channel: discord.TextChannel, config: TraderConfig, pool: list[TraderItem]):
        picks = random.sample(pool, min(2, len(pool)))
        embed = discord.Embed(description=config.spawn_message, colour=discord.Colour.gold())
        if config.image_url:
            embed.set_image(url=config.image_url)
        for item in picks:
            embed.add_field(
                name=item_name(item),
                value=f"{item.price:,} {config.currency_name}",
                inline=True,
            )
        embed.set_footer(text=f"He leaves in {config.stay_minutes} minutes")
        view = TraderView(
            picks, config.currency_name, config.stay_minutes * 60, config.leave_message, config.image_url
        )
        try:
            view.message = await channel.send(embed=embed, view=view)
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
        guilds = GuildConfig.objects.filter(enabled=True, spawn_channel__isnull=False)
        async for guild_config in guilds:
            if random.randint(1, 100) > config.spawn_chance:
                continue
            channel = self.bot.get_channel(guild_config.spawn_channel)
            if not isinstance(channel, discord.TextChannel):
                continue
            await self.spawn(channel, config, pool)

    @roll_loop.before_loop
    async def before_roll_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(WanderingTrader(bot))
