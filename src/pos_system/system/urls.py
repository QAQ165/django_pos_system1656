"""
系统设置路由配置
"""
from django.urls import path
from . import views

app_name = 'system'

urlpatterns = [
    # 系统设置（主路由已指定backend/system/前缀）
    path('', views.admin_settings, name='settings'),
    path('settings/', views.admin_settings, name='settings'),
    path('get-backup-files', views.get_backup_files, name='get_backup_files'),
]
