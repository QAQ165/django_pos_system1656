"""
商品管理路由配置
"""
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # 商品分类管理
    path('categories/', views.admin_product_categories, name='product_categories'),
    path('categories/add/', views.admin_category_add, name='category_add'),
    path('categories/edit/<int:category_id>/', views.admin_category_edit, name='category_edit'),
    path('categories/delete/<int:category_id>/', views.admin_category_delete, name='category_delete'),
    path('categories/children/<int:category_id>/', views.admin_category_children, name='category_children'),
    
    # 商品列表
    path('list/', views.admin_product_list, name='product_list'),
    
    # 库存日志
    path('stock/', views.admin_stock_logs, name='stock'),
    
    # 新增/编辑商品
    path('add/', views.admin_product_add, name='product_add'),
    path('edit/<int:product_id>/', views.admin_product_add, name='product_edit'),
    
    # 删除商品
    path('delete/<int:product_id>/', views.admin_product_delete, name='product_delete'),
    
    # API接口
    path('api/search/', views.api_search_products, name='api_search_products'),
    
    # 批量导入
    path('batch-import/', views.batch_import_products, name='batch_import'),
]
