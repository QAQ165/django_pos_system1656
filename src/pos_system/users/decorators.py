"""
权限装饰器模块
定义各种权限控制装饰器
"""
from django.shortcuts import redirect


def admin_required(view_func):
    """
    管理员权限装饰器
    只允许管理员角色访问
    """
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            return redirect('reports:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_required(view_func):
    """
    管理员和店长权限装饰器
    允许管理员和店长角色访问
    """
    def wrapper(request, *args, **kwargs):
        if request.user.role not in ['admin', 'manager']:
            return redirect('reports:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
