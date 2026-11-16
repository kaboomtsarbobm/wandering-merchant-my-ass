from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0007_instant_merchant"),
    ]

    operations = [
        migrations.AddField(
            model_name="traderconfig",
            name="purchase_image_url",
            field=models.URLField(
                blank=True, max_length=500, help_text="Picture shown in the message the buyer gets after buying"
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="purchase_message",
            field=models.TextField(
                default="You bought **{name}** for {price}!",
                help_text="Message the buyer gets after buying, use {name}, {price} and {user}",
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
    ]
