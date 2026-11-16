import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0004_remove_currency_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="TraderDialogue",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                (
                    "emoji_id",
                    models.BigIntegerField(
                        blank=True, help_text="Emoji ID for this line, replaces the default emoji", null=True
                    ),
                ),
                (
                    "position",
                    models.PositiveIntegerField(default=0, help_text="Lines are shown from lowest to highest"),
                ),
                ("enabled", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "trader dialogue line",
                "verbose_name_plural": "trader dialogue lines",
                "ordering": ["position", "id"],
            },
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="title",
            field=models.CharField(
                blank=True,
                default="Wandering Trader",
                help_text="Heading shown above the message",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="accent_colour",
            field=models.CharField(
                default="#D4A017",
                help_text="Colour of the bar on the side of the message",
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Use a hex colour like #D4A017", regex="^#?[0-9a-fA-F]{6}$"
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="button_style",
            field=models.CharField(
                choices=[("green", "Green"), ("blurple", "Blurple"), ("grey", "Grey"), ("red", "Red")],
                default="green",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="button_label",
            field=models.CharField(
                default="{name} - {price}",
                help_text="Text on the buy buttons, use {name} and {price}",
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="show_timer",
            field=models.BooleanField(default=True, help_text="Show when the trader leaves"),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="emoji_id",
            field=models.BigIntegerField(
                blank=True, help_text="ID of the emoji shown next to everything the trader says", null=True
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="dialogue_seconds",
            field=models.PositiveIntegerField(default=5, help_text="Seconds between dialogue lines (minimum 3)"),
        ),
    ]
