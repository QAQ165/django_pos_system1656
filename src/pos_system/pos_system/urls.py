"""
URL configuration for pos_system project.

项目路由配置
定义了所有应用的URL映射关系
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from users import views as user_views
from reports import views as reports_views

urlpatterns = [
    # 后台管理
    path('admin/', admin.site.urls),
    
    # ==================== 用户认证相关 ====================
    # 登录页面
    path('', user_views.user_login, name='login'),
    path('login/', user_views.user_login, name='login'),
    
    # 退出登录
    path('logout/', user_views.user_logout, name='logout'),
    
    # 验证码
    path('captcha/', user_views.generate_captcha, name='captcha'),


    # 仪表盘路由,返回后台用
    # path('dashboard/', reports_views.dashboard, name='dashboard'),
    # ==================== 各应用路由 ====================
    # 报表统计（包括仪表盘、订单管理、库存管理、数据统计）
    path('reports/', include('reports.urls', namespace='reports')),
    
    # 用户管理（包括员工管理）
    path('users/', include('users.urls', namespace='users')),
    
    # 商品管理
    path('products/', include('products.urls', namespace='products')),
    
    # 系统设置
    path('system/', include('system.urls', namespace='settings')),
    
    # 销售收银
    path('sales/', include('sales.urls', namespace='sales')),
    
    # 会员管理
    path('members/', include('members.urls', namespace='members')),

]

# 开发环境下提供静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # 生产环境下手动提供静态文件和媒体文件服务
    urlpatterns += [
        path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT}),
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
