from django.contrib import admin

from .models import (
    PlayerListing,
    PlayerMerchantSettings,
    PlayerMerchantTemplate,
    TraderConfig,
    TraderDialogue,
    TraderItem,
)


@admin.register(TraderConfig)
class TraderConfigAdmin(admin.ModelAdmin):
    list_display = ("title", "spawn_chance", "interval_minutes", "stay_minutes", "image_url", "enabled")


@admin.register(TraderDialogue)
class TraderDialogueAdmin(admin.ModelAdmin):
    list_display = ("text", "emoji_id", "position", "enabled")
    list_filter = ("enabled",)


@admin.register(TraderItem)
class TraderItemAdmin(admin.ModelAdmin):
    list_display = ("ball", "special", "merchant", "price", "chance", "enabled")
    list_filter = ("enabled", "merchant")


@admin.register(PlayerMerchantSettings)
class PlayerMerchantSettingsAdmin(admin.ModelAdmin):
    list_display = ("enabled", "min_price", "max_price", "max_listings", "cooldown_minutes", "stay_minutes", "fee_percent")


@admin.register(PlayerMerchantTemplate)
class PlayerMerchantTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "image_url", "enabled")
    list_filter = ("enabled",)


@admin.register(PlayerListing)
class PlayerListingAdmin(admin.ModelAdmin):
    list_display = ("ball_instance", "seller", "price", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("seller", "buyer", "ball_instance", "template")

    def has_add_permission(self, request):
        return False


from . import token_admin  # noqa: E402,F401
