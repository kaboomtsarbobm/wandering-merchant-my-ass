import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0010_item_font_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="traderdialogue",
            name="merchant",
            field=models.ForeignKey(
                blank=True,
                help_text="Which merchant says this line, empty means the first merchant",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="dialogue_lines",
                to="wandering_trader.traderconfig",
            ),
        ),
    ]
