from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0003_picture_help_text"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="traderconfig",
            name="currency_name",
        ),
    ]
