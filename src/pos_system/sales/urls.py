from django.urls import path
from . import views

app_name = 'sales'

# 销售模块路由配置
urlpatterns = [
    # 收银台页面
    path('', views.pos_view, name='pos'),
    path('pos/', views.pos_view, name='pos'),
    # 订单管理
    path('orders/', views.order_list, name='order_list'),
    
    # API接口
    path('api/suspend/', views.api_suspend_order, name='api_suspend_order'),
    path('api/get-suspended/', views.api_get_suspended_orders, name='api_get_suspended_orders'),
    path('api/resume/', views.api_resume_order, name='api_resume_order'),
    path('api/checkout/', views.api_checkout, name='api_checkout'),
]