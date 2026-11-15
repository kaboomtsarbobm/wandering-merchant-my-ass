from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="traderconfig",
            name="image_url",
            field=models.URLField(blank=True, help_text="Image shown on the trader message", max_length=500),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="spawn_message",
            field=models.TextField(
                default="A wandering trader has appeared!", help_text="Message shown when the trader spawns"
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="leave_message",
            field=models.TextField(
                default="The wandering trader has moved on. Come back another time.",
                help_text="Message shown when the trader leaves",
            ),
        ),
        migrations.AlterField(
            model_name="traderconfig",
            name="stay_minutes",
            field=models.PositiveIntegerField(default=3, help_text="Minutes the trader stays"),
        ),
    ]
