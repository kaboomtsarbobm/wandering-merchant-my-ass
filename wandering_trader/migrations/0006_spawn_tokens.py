import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0005_ui_and_dialogue"),
    ]

    operations = [
        migrations.CreateModel(
            name="SpawnToken",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "mode",
                    models.CharField(
                        choices=[
                            ("random", "Random ball (normal rarity roll)"),
                            ("rarity_boost", "Rarity boost (leans toward rares)"),
                            ("rares_only", "Rares only (rarity at or below max_rarity)"),
                            ("rarest_first", "Rarest first (heavily favours the rarest)"),
                            ("special_spawn", "Special spawn (ball carries the special)"),
                            ("specific_ball", "Specific ball (always target_ball)"),
                            ("multi_spawn", "Multi spawn (several boosted balls)"),
                            ("lucky_roll", "Lucky roll (percent chance of rarest-first)"),
                            ("common_boost", "Common boost (leans toward commons)"),
                            ("commons_only", "Commons only (rarity at or above min_rarity)"),
                            ("rarity_range", "Rarity range (between min_rarity and max_rarity)"),
                            ("best_of_n", "Best of N (rolls count balls, spawns the rarest)"),
                            ("coin_flip", "Coin flip (50% rarest-first, 50% common boost)"),
                            ("multi_special", "Multi special (several balls, each with the special)"),
                            ("chaos", "Chaos (several balls, each rolled a random way)"),
                        ],
                        default="random",
                        max_length=20,
                    ),
                ),
                (
                    "strength",
                    models.FloatField(
                        default=2.0,
                        help_text="Boost strength for the boost modes. 1 is a normal roll, higher leans harder",
                    ),
                ),
                (
                    "min_rarity",
                    models.FloatField(
                        blank=True,
                        help_text="Lowest rarity value allowed (commons only, rarity range)",
                        null=True,
                    ),
                ),
                (
                    "max_rarity",
                    models.FloatField(
                        blank=True,
                        help_text="Highest rarity value allowed (rares only, rarity range)",
                        null=True,
                    ),
                ),
                (
                    "count",
                    models.PositiveSmallIntegerField(
                        default=3,
                        help_text="How many balls for best of N, multi spawn, multi special and chaos (max 10)",
                    ),
                ),
                (
                    "percent",
                    models.PositiveSmallIntegerField(default=25, help_text="Percent chance for lucky roll"),
                ),
                (
                    "cooldown_minutes",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Minutes a player must wait before using this token again (0 for none)",
                    ),
                ),
                (
                    "ball",
                    models.OneToOneField(
                        help_text="The ball players own that acts as this token",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="spawn_token",
                        to="bd_models.ball",
                    ),
                ),
                (
                    "special",
                    models.ForeignKey(
                        blank=True,
                        help_text="Special for special spawn and multi special",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="bd_models.special",
                    ),
                ),
                (
                    "target_ball",
                    models.ForeignKey(
                        blank=True,
                        help_text="Ball to spawn for specific ball",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="bd_models.ball",
                    ),
                ),
            ],
            options={
                "verbose_name": "spawn token",
                "verbose_name_plural": "spawn tokens",
            },
        ),
    ]
