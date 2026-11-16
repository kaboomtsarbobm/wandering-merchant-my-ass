from django.core.exceptions import ValidationError
from django.db import models

from bd_models.models import Ball, Special


class SpawnToken(models.Model):
    """
    Marks a ball as a token that can be used with /spawn.
    The ball itself is a normal ball that players own. Using the token deletes one copy.
    """

    class Mode(models.TextChoices):
        RANDOM = "random", "Random ball (normal rarity roll)"
        RARITY_BOOST = "rarity_boost", "Rarity boost (leans toward rares)"
        RARES_ONLY = "rares_only", "Rares only (rarity at or below max_rarity)"
        RAREST_FIRST = "rarest_first", "Rarest first (heavily favours the rarest)"
        SPECIAL_SPAWN = "special_spawn", "Special spawn (ball carries the special)"
        SPECIFIC_BALL = "specific_ball", "Specific ball (always target_ball)"
        MULTI_SPAWN = "multi_spawn", "Multi spawn (several boosted balls)"
        LUCKY_ROLL = "lucky_roll", "Lucky roll (percent chance of rarest-first)"
        COMMON_BOOST = "common_boost", "Common boost (leans toward commons)"
        COMMONS_ONLY = "commons_only", "Commons only (rarity at or above min_rarity)"
        RARITY_RANGE = "rarity_range", "Rarity range (between min_rarity and max_rarity)"
        BEST_OF_N = "best_of_n", "Best of N (rolls count balls, spawns the rarest)"
        COIN_FLIP = "coin_flip", "Coin flip (50% rarest-first, 50% common boost)"
        MULTI_SPECIAL = "multi_special", "Multi special (several balls, each with the special)"
        CHAOS = "chaos", "Chaos (several balls, each rolled a random way)"

    id = models.BigAutoField(primary_key=True)
    ball = models.OneToOneField(
        Ball,
        on_delete=models.CASCADE,
        related_name="spawn_token",
        help_text="The ball players own that acts as this token",
    )
    enabled = models.BooleanField(default=True)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.RANDOM)
    strength = models.FloatField(
        default=2.0,
        help_text="Boost strength for the boost modes. 1 is a normal roll, higher leans harder",
    )
    min_rarity = models.FloatField(
        null=True, blank=True, help_text="Lowest rarity value allowed (commons only, rarity range)"
    )
    max_rarity = models.FloatField(
        null=True, blank=True, help_text="Highest rarity value allowed (rares only, rarity range)"
    )
    count = models.PositiveSmallIntegerField(
        default=3, help_text="How many balls for best of N, multi spawn, multi special and chaos (max 10)"
    )
    percent = models.PositiveSmallIntegerField(default=25, help_text="Percent chance for lucky roll")
    special = models.ForeignKey(
        Special,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Special for special spawn and multi special",
    )
    target_ball = models.ForeignKey(
        Ball,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Ball to spawn for specific ball",
    )
    cooldown_minutes = models.PositiveIntegerField(
        default=0, help_text="Minutes a player must wait before using this token again (0 for none)"
    )

    class Meta:
        verbose_name = "spawn token"
        verbose_name_plural = "spawn tokens"

    def __str__(self):
        return f"{self.ball.country} ({self.get_mode_display()})"

    def clean(self):
        errors = {}
        M = self.Mode
        if self.mode == M.RARES_ONLY and self.max_rarity is None:
            errors["max_rarity"] = "Rares only needs a max rarity."
        if self.mode == M.COMMONS_ONLY and self.min_rarity is None:
            errors["min_rarity"] = "Commons only needs a min rarity."
        if self.mode == M.RARITY_RANGE:
            if self.min_rarity is None:
                errors["min_rarity"] = "Rarity range needs a min rarity."
            if self.max_rarity is None:
                errors["max_rarity"] = "Rarity range needs a max rarity."
            if self.min_rarity is not None and self.max_rarity is not None and self.min_rarity > self.max_rarity:
                errors["max_rarity"] = "Max rarity must be at least min rarity."
        if self.mode in (M.SPECIAL_SPAWN, M.MULTI_SPECIAL) and self.special_id is None:
            errors["special"] = "This shit needs a special."
        if self.mode == M.SPECIFIC_BALL and self.target_ball_id is None:
            errors["target_ball"] = "Specific ball needs a target ball."
        if self.percent > 100:
            errors["percent"] = "Percent can't be above 100."
        if errors:
            raise ValidationError(errors)


class InstantMerchantConfig(models.Model):
    """The three items the /merchant command puts in the trader's shop. Only the first row is used."""

    id = models.BigAutoField(primary_key=True)
    item_1 = models.ForeignKey(
        "TraderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Item for slot 1. Empty slots are filled with a random enabled trader item",
    )
    item_2 = models.ForeignKey(
        "TraderItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", help_text="Item for slot 2"
    )
    item_3 = models.ForeignKey(
        "TraderItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", help_text="Item for slot 3"
    )

    class Meta:
        verbose_name = "instant merchant items"
        verbose_name_plural = "instant merchant items"

    def __str__(self):
        return "Instant merchant items"
