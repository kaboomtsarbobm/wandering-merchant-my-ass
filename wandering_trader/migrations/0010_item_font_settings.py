import django.core.validators
from django.db import migrations, models

HELP_FONT = "File name of a font in the package's assets folder, like Pacifico-Regular.ttf. Empty uses the default"
HELP_SIZE = "Biggest size of the item names in the picture, it still shrinks to fit. 0 uses the default"
HELP_COLOUR = "Hex colour of the item text, like #000000. Empty uses the default"
HEX = django.core.validators.RegexValidator(
    message="Use a hex colour like #D4A017", regex="^#?[0-9a-fA-F]{6}$"
)


class Migration(migrations.Migration):
    dependencies = [
        # replace 0009_FILL_IN with the exact name of your 0009 migration file, without the .py
        ("wandering_trader", "0009_scene_background_overlay"),
    ]

    operations = [
        migrations.AddField(
            model_name=model,
            name="item_font",
            field=models.CharField(blank=True, max_length=100, help_text=HELP_FONT),
        )
        for model in ("traderconfig", "playermerchanttemplate")
    ] + [
        migrations.AddField(
            model_name=model,
            name="item_font_size",
            field=models.PositiveSmallIntegerField(default=0, help_text=HELP_SIZE),
        )
        for model in ("traderconfig", "playermerchanttemplate")
    ] + [
        migrations.AddField(
            model_name=model,
            name="item_font_colour",
            field=models.CharField(blank=True, max_length=7, validators=[HEX], help_text=HELP_COLOUR),
        )
        for model in ("traderconfig", "playermerchanttemplate")
    ]
