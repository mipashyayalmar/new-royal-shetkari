from django.contrib import admin

from .models import DemoRecord


@admin.register(DemoRecord)
class DemoRecordAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "kind", "created_at")
    list_filter = ("content_type", "kind")
