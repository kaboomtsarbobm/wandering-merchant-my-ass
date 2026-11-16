from django.core.validators import RegexValidator
from django.db import models

from bd_models.models import Ball, Special

BUTTON_STYLES = [
    ("green", "Green"),
    ("blurple", "Blurple"),
    ("grey", "Grey"),
    ("red", "Red"),
]


class TraderConfig(models.Model):
    enabled = models.BooleanField(default=True)
    spawn_chance = models.PositiveSmallIntegerField(
        default=20, help_text="Chance in percent that the trader shows up on each roll"
    )
    interval_minutes = models.PositiveIntegerField(default=5, help_text="Minutes between rolls")
    stay_minutes = models.PositiveIntegerField(default=3, help_text="Minutes the trader stays")
    image_url = models.URLField(
        max_length=500, blank=True, help_text="Picture placed in the red square of the trader scene"
    )
    spawn_message = models.TextField(
        default="A wandering trader has appeared!", help_text="Message shown when the trader spawns"
    )
    leave_message = models.TextField(
        default="The wandering trader has moved on. Come back another time.",
        help_text="Message shown when the trader leaves",
    )
    purchase_image_url = models.URLField(
        max_length=500, blank=True, help_text="Picture shown in the message the buyer gets after buying"
    )
    purchase_message = models.TextField(
        default="You bought **{name}** for {price}!",
        help_text="Message the buyer gets after buying, use {name}, {price} and {user}",
    )
    title = models.CharField(
        max_length=100, blank=True, default="Wandering Trader", help_text="Heading shown above the message"
    )
    accent_colour = models.CharField(
        max_length=7,
        default="#D4A017",
        validators=[RegexValidator(regex=r"^#?[0-9a-fA-F]{6}$", message="Use a hex colour like #D4A017")],
        help_text="Colour of the bar on the side of the message",
    )
    button_style = models.CharField(max_length=10, choices=BUTTON_STYLES, default="green")
    button_label = models.CharField(
        max_length=80, default="{name} - {price}", help_text="Text on the buy buttons, use {name} and {price}"
    )
    show_timer = models.BooleanField(default=True, help_text="Show when the trader leaves")
    emoji_id = models.BigIntegerField(
        null=True, blank=True, help_text="ID of the emoji shown next to everything the trader says"
    )
    dialogue_seconds = models.PositiveIntegerField(
        default=5, help_text="Seconds between dialogue lines (minimum 3)"
    )

    class Meta:
        verbose_name = "trader settings"
        verbose_name_plural = "trader settings"

    def __str__(self):
        return "Trader settings"


class TraderDialogue(models.Model):
    text = models.TextField()
    emoji_id = models.BigIntegerField(
        null=True, blank=True, help_text="Emoji ID for this line, replaces the default emoji"
    )
    position = models.PositiveIntegerField(default=0, help_text="Lines are shown from lowest to highest")
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "trader dialogue line"
        verbose_name_plural = "trader dialogue lines"

    def __str__(self):
        return self.text[:50]


class TraderItem(models.Model):
    ball = models.ForeignKey(Ball, on_delete=models.CASCADE, related_name="+")
    special = models.ForeignKey(Special, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    price = models.PositiveBigIntegerField(default=100)
    chance = models.PositiveIntegerField(
        default=100,
        help_text="How likely this item is to show up compared to the others, 0 means never in the normal roll",
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "trader item"
        verbose_name_plural = "trader items"

    def __str__(self):
        if self.special:
            return f"{self.special.name} {self.ball.country} - {self.price}"
        return f"{self.ball.country} - {self.price}"


# spawn tokens and the instant merchant settings live in token_models.py
from .token_models import InstantMerchantConfig, SpawnToken  # noqa: E402,F401
