"""
用户认证和管理路由配置
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # 员工管理（主路由已指定/users/前缀）
    path('', views.admin_users, name='admin_users'),
    path('users/', views.admin_users, name='admin_users'),
]
