from django.db import migrations, models

BUTTON_STYLES = [
    ("green", "Green"),
    ("blurple", "Blurple"),
    ("grey", "Grey"),
    ("red", "Red"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("wandering_trader", "0011_dialogue_merchant"),
    ]

    operations = [
        migrations.AddField(
            model_name="traderconfig",
            name="confirm_purchase",
            field=models.BooleanField(
                default=False, help_text="Ask the buyer to confirm before the purchase goes through"
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="confirm_message",
            field=models.TextField(
                default="Are you sure you want to buy **{name}** for {price}?",
                help_text="Question shown to the buyer, use {name}, {price} and {user}",
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="confirm_yes_label",
            field=models.CharField(
                default="YESSS!!!", max_length=80, help_text="Text on the button that confirms the purchase"
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="confirm_no_label",
            field=models.CharField(
                default="FUCK NO", max_length=80, help_text="Text on the button that cancels the purchase"
            ),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="confirm_yes_style",
            field=models.CharField(choices=BUTTON_STYLES, default="green", max_length=10),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="confirm_no_style",
            field=models.CharField(choices=BUTTON_STYLES, default="red", max_length=10),
        ),
        migrations.AddField(
            model_name="traderconfig",
            name="confirm_cancel_message",
            field=models.TextField(
                default="Okay, no purchase.",
                help_text="Message shown when the buyer cancels, use {name} and {price}",
            ),
        ),
    ]
