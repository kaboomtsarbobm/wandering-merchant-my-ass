from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0008_merchants_and_player_listings"),
    ]

    operations = [
        migrations.AddField(
            model_name="traderconfig",
            name="background_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                help_text="Replaces the scene background, keep the same layout as the default so the picture and names line up. Empty uses the default",
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="overlay_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                help_text="Transparent PNG drawn over the whole scene, like a frame or effects. Empty means none",
            ),
        ),
        migrations.AddField(
            model_name="playermerchanttemplate",
            name="background_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                help_text="Replaces the scene background, keep the same layout as the default so the picture and names line up. Empty uses the default",
            ),
        ),
        migrations.AddField(
            model_name="playermerchanttemplate",
            name="overlay_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                help_text="Transparent PNG drawn over the whole scene, like a frame or effects. Empty means none",
            ),
        ),
    ]
