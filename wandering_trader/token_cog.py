from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from django.db.models import Count

from ballsdex.packages.countryballs.countryball import BallSpawnView
from bd_models.models import BallInstance, balls

from .token_models import SpawnToken

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.wandering_trader.tokens")

M = SpawnToken.Mode

# In BallsDex a higher rarity number means a more common ball, and the spawn weight is the
# rarity value itself. weight = rarity ** exponent, so 1 is a normal roll, below 1 leans
# toward rares (negative inverts the odds), above 1 leans toward commons.
NORMAL = 1.0
RAREST = -4.0
UNIFORM = 0.0

MAX_MULTI = 5


class TokenError(Exception):
    """Raised when a token can't be used, with a message safe to show to the player."""


def _pick(pool, exponent: float):
    weights = [max(float(b.rarity), 1e-9) ** exponent for b in pool]
    return random.choices(pool, weights=weights, k=1)[0]


def build_plan(token: SpawnToken) -> list[tuple]:
    """Returns a list of (ball, special | None) to spawn for this token."""
    mode = token.mode
    strength = max(float(token.strength), 0.1)
    boost = 1.0 - strength
    common = 1.0 + strength
    n = max(1, min(int(token.count), 10))
    multi = max(1, min(n, MAX_MULTI))

    if mode == M.SPECIFIC_BALL:
        if token.target_ball is None:
            raise TokenError("The tokens power isnt quite ready yet, Check back later!")
        return [(token.target_ball, None)]

    pool = [b for b in balls.values() if b.enabled and b.rarity > 0]

    if mode == M.RARES_ONLY and token.max_rarity is not None:
        pool = [b for b in pool if b.rarity <= token.max_rarity]
    elif mode == M.COMMONS_ONLY and token.min_rarity is not None:
        pool = [b for b in pool if b.rarity >= token.min_rarity]
    elif mode == M.RARITY_RANGE and token.min_rarity is not None and token.max_rarity is not None:
        pool = [b for b in pool if token.min_rarity <= b.rarity <= token.max_rarity]
    if not pool:
        raise TokenError("Token error, Check back later!")

    if mode in (M.SPECIAL_SPAWN, M.MULTI_SPECIAL) and token.special is None:
        raise TokenError("Token error, Check back later!")

    if mode in (M.RANDOM, M.RARES_ONLY, M.COMMONS_ONLY, M.RARITY_RANGE):
        return [(_pick(pool, NORMAL), None)]
    if mode == M.RARITY_BOOST:
        return [(_pick(pool, boost), None)]
    if mode == M.RAREST_FIRST:
        return [(_pick(pool, RAREST), None)]
    if mode == M.COMMON_BOOST:
        return [(_pick(pool, common), None)]
    if mode == M.SPECIAL_SPAWN:
        return [(_pick(pool, NORMAL), token.special)]
    if mode == M.MULTI_SPAWN:
        return [(_pick(pool, boost), None) for _ in range(multi)]
    if mode == M.LUCKY_ROLL:
        lucky = random.randint(1, 100) <= token.percent
        return [(_pick(pool, RAREST if lucky else NORMAL), None)]
    if mode == M.BEST_OF_N:
        rolls = [_pick(pool, NORMAL) for _ in range(n)]
        return [(min(rolls, key=lambda b: b.rarity), None)]
    if mode == M.COIN_FLIP:
        return [(_pick(pool, RAREST if random.random() < 0.5 else common), None)]
    if mode == M.MULTI_SPECIAL:
        return [(_pick(pool, NORMAL), token.special) for _ in range(multi)]
    if mode == M.CHAOS:
        methods = [NORMAL, boost, RAREST, common, UNIFORM]
        return [(_pick(pool, random.choice(methods)), None) for _ in range(multi)]
    raise TokenError("Token error, Check back later!")


class SpawnTokens(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}
        # cooldowns only live in memory, so they reset when the bot restarts
        self._last_used: dict[tuple[int, int], float] = {}

    async def token_autocomplete(self, interaction: discord.Interaction["BallsDexBot"], current: str):
        rows = (
            BallInstance.objects.filter(
                player__discord_id=interaction.user.id, locked__isnull=True, ball__spawn_token__enabled=True
            )
            .order_by()
            .values("ball_id", "ball__country")
            .annotate(n=Count("pk"))
        )
        choices: list[app_commands.Choice[str]] = []
        async for row in rows:
            if current.lower() not in row["ball__country"].lower():
                continue
            choices.append(
                app_commands.Choice(name=f"{row['ball__country']} (x{row['n']})"[:100], value=str(row["ball_id"]))
            )
        return choices[:25]

    @app_commands.command(name="spawn", description="Use a token to spawn something in this channel")
    @app_commands.describe(token="The token to use")
    @app_commands.guild_only()
    async def spawn(self, interaction: discord.Interaction["BallsDexBot"], token: str):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("You can only use tokens in a text channel.", ephemeral=True)
            return

        lock = self._locks.setdefault(interaction.user.id, asyncio.Lock())
        if lock.locked():
            await interaction.followup.send("Your using one!", ephemeral=True)
            return

        async with lock:
            try:
                ball_id = int(token)
            except ValueError:
                await interaction.followup.send("Pick a token from the list.", ephemeral=True)
                return

            config = (
                await SpawnToken.objects.select_related("ball", "special", "target_ball")
                .filter(ball_id=ball_id, enabled=True)
                .afirst()
            )
            if config is None:
                await interaction.followup.send("Hey, no.", ephemeral=True)
                return

            instance = await BallInstance.objects.filter(
                player__discord_id=interaction.user.id, ball_id=ball_id, locked__isnull=True
            ).afirst()
            if instance is None:
                await interaction.followup.send(f"You don't have a **{config.ball.country}**.", ephemeral=True)
                return

            key = (interaction.user.id, ball_id)
            if config.cooldown_minutes:
                wait = self._last_used.get(key, 0) + config.cooldown_minutes * 60 - time.monotonic()
                if wait > 0:
                    await interaction.followup.send(
                        f"This token is on cooldown, try again in {int(wait // 60) + 1} minute(s).", ephemeral=True
                    )
                    return

            try:
                plan = build_plan(config)
            except TokenError as e:
                await interaction.followup.send(str(e), ephemeral=True)
                return

            # lock the token so it can't be traded away while the spawn is happening
            await instance.lock_for_trade()
            spawned = 0
            try:
                for ball, special in plan:
                    view = BallSpawnView(self.bot, ball)
                    view.algo = "spawn_token"
                    view.special = special
                    try:
                        if await view.spawn(channel):
                            spawned += 1
                    except Exception:
                        log.exception("Spawn token failed to spawn %s", ball)
                    if len(plan) > 1:
                        await asyncio.sleep(0.6)

                if not spawned:
                    await instance.unlock()
                    await interaction.followup.send(
                        "Token error, I might not have permissions in this channel, please enable permissions for me to spawn here.",
                        ephemeral=True,
                    )
                    return

                try:
                    await instance.adelete()
                except Exception:
                    log.exception("Could not delete used spawn token %s", instance.pk)
                    await instance.unlock()
                    await interaction.followup.send(
                        "Hm, the random spawned, but the token wasnt removed. Ping @kaboomtsarbobm (when hes awake) for the bug!", ephemeral=True
                    )
                    return
            except BaseException:
                # something unexpected, never leave the token stuck locked
                if spawned == 0:
                    try:
                        await instance.unlock()
                    except Exception:
                        log.exception("Could not unlock spawn token %s", instance.pk)
                raise

            self._last_used[key] = time.monotonic()
            await interaction.followup.send(
                f"Used **{config.ball.country}**. Spawned {spawned} ball{'s' if spawned != 1 else ''}!",
                ephemeral=True,
            )

    @spawn.autocomplete("token")
    async def spawn_token_autocomplete(self, interaction: discord.Interaction["BallsDexBot"], current: str):
        return await self.token_autocomplete(interaction, current)
