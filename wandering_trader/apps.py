from django.apps import AppConfig


class WanderingTraderConfig(AppConfig):
    name = "wandering_trader"
    verbose_name = "Wandering Trader"
    default_auto_field = "django.db.models.BigAutoField"
    dpy_package = "wandering_trader.cog"
