from django.contrib import admin
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'card_no', 'name', 'phone', 'points', 'balance', 'level', 'create_time', 'last_visit_time')
    list_filter = ('level', 'create_time')
    search_fields = ('card_no', 'name', 'phone')
    list_editable = ('points', 'balance', 'level')
    readonly_fields = ('create_time', 'last_visit_time')