from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    # 在用户列表页面显示的字段
    list_display = ('id', 'username', 'email', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('id',)

    # 编辑用户时，将 role 字段添加到字段集中
    fieldsets = BaseUserAdmin.fieldsets + (
        ('角色信息', {'fields': ('role',)}),
    )
    # 添加用户时的字段集
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('角色信息', {'fields': ('role',)}),
    )

admin.site.register(User, UserAdmin)