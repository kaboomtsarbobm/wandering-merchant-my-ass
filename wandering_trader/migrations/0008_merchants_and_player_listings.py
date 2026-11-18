import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0007_instant_merchant"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="traderconfig",
            options={"verbose_name": "merchant", "verbose_name_plural": "merchants"},
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="purchase_image_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                help_text="Picture shown on the trader after a purchase, used when the item has none of its own",
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="purchase_message",
            field=models.TextField(
                default="{user} bought **{name}** for {price}!",
                help_text="Message shown on the trader after a purchase, use {name}, {price} and {user}",
            ),
        ),
        migrations.AddField(
            model_name="traderitem",
            name="merchant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="items",
                to="wandering_trader.traderconfig",
                help_text="Which merchant sells this item, empty means the first merchant",
            ),
        ),
        migrations.AddField(
            model_name="traderitem",
            name="chance",
            field=models.PositiveIntegerField(
                default=100,
                help_text="How likely this item is to show up compared to the others, 0 means never in the normal roll",
            ),
        ),
        migrations.AddField(
            model_name="traderitem",
            name="purchase_message",
            field=models.TextField(
                blank=True,
                help_text="Message shown on the trader when this item is bought, use {name}, {price} and {user}. Empty uses the merchant's message",
            ),
        ),
        migrations.AddField(
            model_name="traderitem",
            name="purchase_image_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                help_text="Picture shown on the trader when this item is bought. Empty uses the merchant's picture",
            ),
        ),
        migrations.CreateModel(
            name="PlayerMerchantSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=True, help_text="Turn player merchants on or off")),
                (
                    "min_price",
                    models.PositiveBigIntegerField(default=100, help_text="Lowest price a player can ask"),
                ),
                (
                    "max_price",
                    models.PositiveBigIntegerField(default=1000000, help_text="Highest price a player can ask"),
                ),
                (
                    "max_listings",
                    models.PositiveIntegerField(default=2, help_text="How many listings a player can have at once"),
                ),
                (
                    "cooldown_minutes",
                    models.PositiveIntegerField(default=5, help_text="Minutes a player waits between listings"),
                ),
                (
                    "stay_minutes",
                    models.PositiveIntegerField(default=10, help_text="Minutes a listing stays up"),
                ),
                (
                    "fee_percent",
                    models.PositiveSmallIntegerField(
                        default=5,
                        validators=[django.core.validators.MaxValueValidator(100)],
                        help_text="Percent of the price taken from the seller on each sale",
                    ),
                ),
            ],
            options={
                "verbose_name": "player merchant settings",
                "verbose_name_plural": "player merchant settings",
            },
        ),
        migrations.CreateModel(
            name="PlayerMerchantTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "name",
                    models.CharField(max_length=100, help_text="Name players pick, also the heading of the listing"),
                ),
                (
                    "image_url",
                    models.URLField(
                        blank=True,
                        max_length=500,
                        help_text="Picture placed in the red square of the trader scene",
                    ),
                ),
                (
                    "spawn_message",
                    models.TextField(
                        default="{seller} is selling **{name}** for {price}!",
                        help_text="Message shown when the listing appears, use {seller}, {name} and {price}",
                    ),
                ),
                (
                    "purchase_image_url",
                    models.URLField(
                        blank=True,
                        max_length=500,
                        help_text="Picture shown after the item is bought, empty keeps the normal one",
                    ),
                ),
                (
                    "purchase_message",
                    models.TextField(
                        default="{user} bought **{name}** from {seller} for {price}!",
                        help_text="Message shown after the item is bought, use {seller}, {user}, {name} and {price}",
                    ),
                ),
                (
                    "leave_message",
                    models.TextField(
                        default="{seller}'s merchant has moved on.",
                        help_text="Message shown when the listing runs out, use {seller} and {name}",
                    ),
                ),
                (
                    "accent_colour",
                    models.CharField(
                        default="#4C9BE8",
                        max_length=7,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Use a hex colour like #D4A017", regex="^#?[0-9a-fA-F]{6}$"
                            )
                        ],
                        help_text="Colour of the bar on the side of the message",
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "player merchant style",
                "verbose_name_plural": "player merchant styles",
            },
        ),
        migrations.CreateModel(
            name="PlayerListing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price", models.PositiveBigIntegerField()),
                ("fee_percent", models.PositiveSmallIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("sold", "Sold"),
                            ("expired", "Expired"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="active",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "ball_instance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="bd_models.ballinstance",
                    ),
                ),
                (
                    "buyer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="bd_models.player",
                    ),
                ),
                (
                    "seller",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="bd_models.player",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wandering_trader.playermerchanttemplate",
                    ),
                ),
            ],
            options={
                "verbose_name": "player listing",
                "verbose_name_plural": "player listings",
                "ordering": ["-created_at"],
            },
        ),
    ]
