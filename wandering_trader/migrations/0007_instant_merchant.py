import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0006_spawn_tokens"),
    ]

    operations = [
        migrations.CreateModel(
            name="InstantMerchantConfig",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "item_1",
                    models.ForeignKey(
                        blank=True,
                        help_text="Item for slot 1. Empty slots are filled with a random enabled trader item",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wandering_trader.traderitem",
                    ),
                ),
                (
                    "item_2",
                    models.ForeignKey(
                        blank=True,
                        help_text="Item for slot 2",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wandering_trader.traderitem",
                    ),
                ),
                (
                    "item_3",
                    models.ForeignKey(
                        blank=True,
                        help_text="Item for slot 3",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wandering_trader.traderitem",
                    ),
                ),
            ],
            options={
                "verbose_name": "instant merchant items",
                "verbose_name_plural": "instant merchant items",
            },
        ),
    ]
