from django.core.validators import MaxValueValidator, RegexValidator
from django.db import models

from bd_models.models import Ball, BallInstance, Player, Special

BUTTON_STYLES = [
    ("green", "Green"),
    ("blurple", "Blurple"),
    ("grey", "Grey"),
    ("red", "Red"),
]

LISTING_STATUSES = [
    ("active", "Active"),
    ("sold", "Sold"),
    ("expired", "Expired"),
    ("cancelled", "Cancelled"),
]

HEX_COLOUR = RegexValidator(regex=r"^#?[0-9a-fA-F]{6}$", message="Use a hex colour like #D4A017")


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
    background_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Replaces the scene background, keep the same layout as the default so the picture and names line up. Empty uses the default",
    )
    overlay_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Transparent PNG drawn over the whole scene, like a frame or effects. Empty means none",
    )
    spawn_message = models.TextField(
        default="A wandering trader has appeared!", help_text="Message shown when the trader spawns"
    )
    leave_message = models.TextField(
        default="The wandering trader has moved on. Come back another time.",
        help_text="Message shown when the trader leaves",
    )
    purchase_image_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Picture shown on the trader after a purchase, used when the item has none of its own",
    )
    purchase_message = models.TextField(
        default="{user} bought **{name}** for {price}!",
        help_text="Message shown on the trader after a purchase, use {name}, {price} and {user}",
    )
    title = models.CharField(
        max_length=100, blank=True, default="Wandering Trader", help_text="Heading shown above the message"
    )
    accent_colour = models.CharField(
        max_length=7,
        default="#D4A017",
        validators=[HEX_COLOUR],
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
        verbose_name = "merchant"
        verbose_name_plural = "merchants"

    def __str__(self):
        return self.title or f"Merchant {self.pk}"


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
    merchant = models.ForeignKey(
        TraderConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
        help_text="Which merchant sells this item, empty means the first merchant",
    )
    ball = models.ForeignKey(Ball, on_delete=models.CASCADE, related_name="+")
    special = models.ForeignKey(Special, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    price = models.PositiveBigIntegerField(default=100)
    chance = models.PositiveIntegerField(
        default=100,
        help_text="How likely this item is to show up compared to the others, 0 means never in the normal roll",
    )
    purchase_message = models.TextField(
        blank=True,
        help_text="Message shown on the trader when this item is bought, use {name}, {price} and {user}. Empty uses the merchant's message",
    )
    purchase_image_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Picture shown on the trader when this item is bought. Empty uses the merchant's picture",
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "trader item"
        verbose_name_plural = "trader items"

    def __str__(self):
        if self.special:
            return f"{self.special.name} {self.ball.country} - {self.price}"
        return f"{self.ball.country} - {self.price}"


class PlayerMerchantSettings(models.Model):
    enabled = models.BooleanField(default=True, help_text="Turn player merchants on or off")
    min_price = models.PositiveBigIntegerField(default=100, help_text="Lowest price a player can ask")
    max_price = models.PositiveBigIntegerField(default=1000000, help_text="Highest price a player can ask")
    max_listings = models.PositiveIntegerField(default=2, help_text="How many listings a player can have at once")
    cooldown_minutes = models.PositiveIntegerField(default=5, help_text="Minutes a player waits between listings")
    stay_minutes = models.PositiveIntegerField(default=10, help_text="Minutes a listing stays up")
    fee_percent = models.PositiveSmallIntegerField(
        default=5,
        validators=[MaxValueValidator(100)],
        help_text="Percent of the price taken from the seller on each sale",
    )

    class Meta:
        verbose_name = "player merchant settings"
        verbose_name_plural = "player merchant settings"

    def __str__(self):
        return "Player merchant settings"


class PlayerMerchantTemplate(models.Model):
    name = models.CharField(max_length=100, help_text="Name players pick, also the heading of the listing")
    image_url = models.URLField(
        max_length=500, blank=True, help_text="Picture placed in the red square of the trader scene"
    )
    background_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Replaces the scene background, keep the same layout as the default so the picture and names line up. Empty uses the default",
    )
    overlay_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Transparent PNG drawn over the whole scene, like a frame or effects. Empty means none",
    )
    spawn_message = models.TextField(
        default="{seller} is selling **{name}** for {price}!",
        help_text="Message shown when the listing appears, use {seller}, {name} and {price}",
    )
    purchase_image_url = models.URLField(
        max_length=500, blank=True, help_text="Picture shown after the item is bought, empty keeps the normal one"
    )
    purchase_message = models.TextField(
        default="{user} bought **{name}** from {seller} for {price}!",
        help_text="Message shown after the item is bought, use {seller}, {user}, {name} and {price}",
    )
    leave_message = models.TextField(
        default="{seller}'s merchant has moved on.",
        help_text="Message shown when the listing runs out, use {seller} and {name}",
    )
    accent_colour = models.CharField(
        max_length=7,
        default="#4C9BE8",
        validators=[HEX_COLOUR],
        help_text="Colour of the bar on the side of the message",
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "player merchant style"
        verbose_name_plural = "player merchant styles"

    def __str__(self):
        return self.name


class PlayerListing(models.Model):
    seller = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="+")
    buyer = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    ball_instance = models.ForeignKey(BallInstance, on_delete=models.CASCADE, related_name="+")
    template = models.ForeignKey(
        PlayerMerchantTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    price = models.PositiveBigIntegerField()
    fee_percent = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=10, choices=LISTING_STATUSES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "player listing"
        verbose_name_plural = "player listings"

    def __str__(self):
        return f"Listing {self.pk} - {self.price} ({self.status})"


# spawn tokens and the instant merchant settings live in token_models.py
from .token_models import InstantMerchantConfig, SpawnToken  # noqa: E402,F401
