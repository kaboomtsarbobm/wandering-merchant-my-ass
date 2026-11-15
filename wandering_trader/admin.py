from django.contrib import admin

from .models import TraderConfig, TraderItem


@admin.register(TraderConfig)
class TraderConfigAdmin(admin.ModelAdmin):
    list_display = ("currency_name", "spawn_chance", "interval_minutes", "stay_minutes", "image_url", "enabled")


@admin.register(TraderItem)
class TraderItemAdmin(admin.ModelAdmin):
    list_display = ("ball", "special", "price", "enabled")
    list_filter = ("enabled",)
