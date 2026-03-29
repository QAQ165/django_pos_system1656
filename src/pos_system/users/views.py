from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.conf import settings
import random
import string
import os
import time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from .decorators import admin_required, manager_required
from products.models import Category, Product, StockLog


def generate_captcha(request):
    """
    生成图形验证码
    使用PIL库生成包含随机字符的图片
    """
    # 生成4位随机验证码（字母+数字）
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # 将验证码存入session，用于后续验证
    request.session['captcha'] = captcha_text
    
    # 创建图片
    width, height = 120, 40
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 添加干扰线
    for i in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
    # 添加干扰点
    for i in range(30):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
    # 绘制文字
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    for i, char in enumerate(captcha_text):
        x = 20 + i * 25
        y = 5 + random.randint(-5, 5)
        draw.text((x, y), char, font=font, fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)))
    
    # 将图片转换为字节流
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    
    return HttpResponse(buffer.getvalue(), content_type='image/png')


def user_login(request):
    """
    用户登录视图
    处理用户登录请求，验证用户名、密码和验证码
    支持普通表单提交和AJAX请求
    """

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        captcha = request.POST.get('captcha', '').upper()

        # 验证验证码
        session_captcha = request.session.get('captcha', '')
        if captcha != session_captcha:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': {'captcha': '验证码错误'}
                })
            return render(request, 'public/login.html', {
                'error': '验证码错误'
            })
        
        # 验证用户名和密码
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # 根据用户角色确定跳转页面
            if user.role in ['admin', 'manager']:
                redirect_url = '/reports/dashboard/'
            else:
                redirect_url = '/sales/pos'
            
            # AJAX请求返回JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'redirect_url': redirect_url
                })
            # 普通表单提交直接重定向
            return redirect(redirect_url)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': {'general': '用户名或密码错误'}
                })
            return render(request, 'public/login.html', {
                'error': '用户名或密码错误'
            })
    
    return render(request, 'public/login.html')


def user_logout(request):
    """
    用户登出视图
    清除用户会话并重定向到登录页面
    """
    logout(request)
    return redirect('login')



@login_required
@admin_required
def admin_users(request):
    """
    员工管理页面
    仅管理员可访问
    """
    from .models import User
    users = User.objects.all().order_by('-id')
    
    context = {
        'page_title': '员工管理',
        'user': request.user,
        'users': users,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'users/users_content.html', context)
    
    return render(request, 'users/users.html', context)


@login_required
@manager_required
def admin_reports(request):
    """
    数据统计页面
    管理员和店长可访问
    """
    context = {
        'page_title': '数据统计',
        'user': request.user,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'public/empty_page.html', context)
    
    return render(request, 'public/empty_page.html', context)



    
    


from django.db import models
