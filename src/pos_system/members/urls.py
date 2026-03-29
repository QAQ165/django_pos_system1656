"""
会员管理路由配置
"""
from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    # 会员管理列表
    path('', views.member_list, name='member_list'),
    path('list/', views.member_list, name='member_list'),
    # 会员增删改查
    path('add/', views.member_add, name='member_add'),
    path('edit/', views.member_edit, name='member_edit'),
    path('delete/<int:member_id>/', views.member_delete, name='member_delete'),
    # 会员充值和积分调整
    path('recharge/', views.member_recharge, name='member_recharge'),
    path('adjust-points/', views.member_adjust_points, name='member_adjust_points'),
    
    # API接口
    path('api/search/', views.api_search_members, name='api_search_members'),
]
