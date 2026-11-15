import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("bd_models", "__latest__"),
    ]

    operations = [
        migrations.CreateModel(
            name="TraderConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=True)),
                ("currency_name", models.CharField(default="bbux", max_length=64)),
                (
                    "spawn_chance",
                    models.PositiveSmallIntegerField(
                        default=20, help_text="Chance in percent that the trader shows up on each roll"
                    ),
                ),
                ("interval_minutes", models.PositiveIntegerField(default=5, help_text="Minutes between rolls")),
                ("stay_minutes", models.PositiveIntegerField(default=5, help_text="Minutes the trader stays")),
            ],
            options={
                "verbose_name": "trader settings",
                "verbose_name_plural": "trader settings",
            },
        ),
        migrations.CreateModel(
            name="TraderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price", models.PositiveBigIntegerField(default=100)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "ball",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="+", to="bd_models.ball"
                    ),
                ),
                (
                    "special",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="bd_models.special",
                    ),
                ),
            ],
            options={
                "verbose_name": "trader item",
                "verbose_name_plural": "trader items",
            },
        ),
    ]
