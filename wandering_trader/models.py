from django.db import models

from bd_models.models import Ball, Special


class TraderConfig(models.Model):
    enabled = models.BooleanField(default=True)
    spawn_chance = models.PositiveSmallIntegerField(
        default=20, help_text="Chance in percent that the trader shows up on each roll"
    )
    interval_minutes = models.PositiveIntegerField(default=5, help_text="Minutes between rolls")
    stay_minutes = models.PositiveIntegerField(default=3, help_text="Minutes the trader stays")
    image_url = models.URLField(max_length=500, blank=True, help_text="Picture placed in the red square of the trader scene")
    spawn_message = models.TextField(
        default="A wandering trader has appeared!", help_text="Message shown when the trader spawns"
    )
    leave_message = models.TextField(
        default="The wandering trader has moved on. Come back another time.",
        help_text="Message shown when the trader leaves",
    )

    class Meta:
        verbose_name = "trader settings"
        verbose_name_plural = "trader settings"

    def __str__(self):
        return "Trader settings"


class TraderItem(models.Model):
    ball = models.ForeignKey(Ball, on_delete=models.CASCADE, related_name="+")
    special = models.ForeignKey(Special, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    price = models.PositiveBigIntegerField(default=100)
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "trader item"
        verbose_name_plural = "trader items"

    def __str__(self):
        if self.special:
            return f"{self.special.name} {self.ball.country} - {self.price}"
        return f"{self.ball.country} - {self.price}"
