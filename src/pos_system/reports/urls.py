"""
报表和数据展示路由配置
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [

    path('', views.dashboard, name='dashboard'),

    # 仪表盘
    path('dashboard/', views.dashboard, name='dashboard'),
    

    # 数据统计
    path('reports/', views.admin_reports, name='reports'),
    
    # API接口
    path('api/overview/', views.get_overview_data, name='get_overview_data'),
    path('api/trend/', views.get_trend_data, name='get_trend_data'),
    path('api/hot-products/', views.get_hot_products, name='get_hot_products'),
    path('api/sales-rank/', views.get_sales_rank, name='get_sales_rank'),
    path('api/profit-rank/', views.get_profit_rank, name='get_profit_rank'),
    path('api/member-consumption/', views.get_member_consumption, name='get_member_consumption'),
    path('api/new-members/', views.get_new_members, name='get_new_members'),
    path('api/repurchase-rate/', views.get_repurchase_rate, name='get_repurchase_rate'),
    
    # 仪表盘API接口
    path('api/dashboard/sales-trend/', views.get_dashboard_sales_trend, name='get_dashboard_sales_trend'),
    path('api/dashboard/sales-rank/', views.get_dashboard_sales_rank, name='get_dashboard_sales_rank'),
    path('api/dashboard/stock-warning/', views.get_dashboard_stock_warning, name='get_dashboard_stock_warning'),
    path('api/dashboard/recent-orders/', views.get_dashboard_recent_orders, name='get_dashboard_recent_orders'),
    path('api/dashboard/expiry-warning/', views.get_dashboard_expiry_warning, name='get_dashboard_expiry_warning'),
]
