from django.contrib import admin

from . import token_admin  # noqa: F401
from .models import TraderConfig, TraderDialogue, TraderItem


@admin.register(TraderConfig)
class TraderConfigAdmin(admin.ModelAdmin):
    list_display = ("title", "spawn_chance", "interval_minutes", "stay_minutes", "image_url", "enabled")


@admin.register(TraderDialogue)
class TraderDialogueAdmin(admin.ModelAdmin):
    list_display = ("text", "emoji_id", "position", "enabled")
    list_filter = ("enabled",)


@admin.register(TraderItem)
class TraderItemAdmin(admin.ModelAdmin):
    list_display = ("ball", "special", "price", "enabled")
    list_filter = ("enabled",)
