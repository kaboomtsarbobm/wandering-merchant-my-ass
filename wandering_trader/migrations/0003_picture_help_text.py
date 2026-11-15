from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0002_trader_message_and_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="traderconfig",
            name="image_url",
            field=models.URLField(
                blank=True, help_text="Picture placed in the red square of the trader scene", max_length=500
            ),
        ),
    ]
