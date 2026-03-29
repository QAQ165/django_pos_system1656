from django.contrib import admin
from .models import SystemSettings

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'value', 'description')
    search_fields = ('key', 'description')
    list_editable = ('value',)