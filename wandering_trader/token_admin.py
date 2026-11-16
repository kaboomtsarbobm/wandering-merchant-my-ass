from django.contrib import admin

from .token_models import InstantMerchantConfig, SpawnToken


@admin.register(SpawnToken)
class SpawnTokenAdmin(admin.ModelAdmin):
    list_display = ("ball", "mode", "strength", "count", "cooldown_minutes", "enabled")
    list_filter = ("mode", "enabled")
    fieldsets = (
        (None, {"fields": ("ball", "enabled", "mode", "cooldown_minutes")}),
        ("Rolling", {"fields": ("strength", "min_rarity", "max_rarity", "count", "percent")}),
        ("Targets", {"fields": ("special", "target_ball")}),
    )


@admin.register(InstantMerchantConfig)
class InstantMerchantConfigAdmin(admin.ModelAdmin):
    list_display = ("__str__", "item_1", "item_2", "item_3")
