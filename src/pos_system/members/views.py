from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q
import random
import time

from decimal import Decimal

from members.models import Member
from products.models import Product
from users.decorators import manager_required


# 会员等级选项
MEMBER_LEVELS = [
    ('普通', '普通'),
    ('银卡', '银卡'),
    ('金卡', '金卡'),
    ('钻石', '钻石'),
]


@login_required
@manager_required
def member_list(request):
    """
    会员管理页面
    管理员和店长可访问
    支持分页、手机号搜索、会员名称搜索、会员等级搜索、卡号搜索
    """
    # 获取筛选参数
    page = request.GET.get('page', 1)
    phone_search = request.GET.get('phone', '')
    name_search = request.GET.get('name', '')
    level_filter = request.GET.get('level', '')
    card_no_search = request.GET.get('card_no', '')
    
    # 基础查询
    members = Member.objects.all().order_by('-create_time')
    
    # 按手机号搜索
    if phone_search:
        members = members.filter(phone__icontains=phone_search)
    
    # 按会员名称搜索
    if name_search:
        members = members.filter(name__icontains=name_search)
    
    # 按会员等级筛选
    if level_filter:
        members = members.filter(level=level_filter)
    
    # 按卡号搜索
    if card_no_search:
        members = members.filter(card_no__icontains=card_no_search)
    
    # 分页
    paginator = Paginator(members, 20)
    try:
        members_page = paginator.page(page)
    except PageNotAnInteger:
        members_page = paginator.page(1)
    except EmptyPage:
        members_page = paginator.page(paginator.num_pages)
    
    context = {
        'page_title': '会员管理',
        'user': request.user,
        'members': members_page,
        'member_levels': MEMBER_LEVELS,
        'phone_search': phone_search,
        'name_search': name_search,
        'level_filter': level_filter,
        'card_no_search': card_no_search,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'members/member_list_content.html', context)
    
    return render(request, 'members/member_list.html', context)


@login_required
@manager_required
def member_add(request):
    """
    新增会员
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        level = request.POST.get('level', '普通')
        
        if not name:
            return JsonResponse({'success': False, 'message': '会员姓名不能为空'})
        
        # 生成卡号：时间戳+手机号+4位随机数
        timestamp = str(int(time.time()))
        phone_part = phone[-4:] if phone and len(phone) >= 4 else '0000'
        random_part = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        card_no = timestamp + phone_part + random_part
        
        # 检查手机号是否已存在
        if phone and Member.objects.filter(phone=phone).exists():
            return JsonResponse({'success': False, 'message': '该手机号已注册'})
        
        try:
            member = Member.objects.create(
                card_no=card_no,
                name=name,
                phone=phone,
                level=level,
                points=0,
                balance=0.00
            )
            return JsonResponse({
                'success': True, 
                'message': '会员添加成功',
                'member_id': member.id,
                'card_no': member.card_no
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'添加失败：{str(e)}'})
    
    return JsonResponse({'success': False, 'message': '请求方式错误'})




@login_required
def api_search_members(request):
    """
    收银台会员搜索API
    支持按手机号模糊搜索会员
    返回JSON格式数据
    """
    phone = request.GET.get('phone', '').strip()
    
    if not phone:
        return JsonResponse({'success': False, 'message': '请输入手机号'})
    
    # 按手机号模糊搜索
    members = Member.objects.filter(phone__icontains=phone)[:10]
    
    # 构建返回数据
    data = []
    for member in members:
        data.append({
            'id': member.id,
            'card_no': member.card_no,
            'name': member.name,
            'phone': member.phone,
            'level': member.level,
            'balance': float(member.balance),
            'points': member.points
        })
    
    return JsonResponse({
        'success': True,
        'data': data,
        'count': len(data)
    })


@login_required
@manager_required
def member_edit(request):
    """
    编辑会员
    """
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        level = request.POST.get('level', '普通')
        
        if not member_id:
            return JsonResponse({'success': False, 'message': '会员ID不能为空'})
        
        if not name:
            return JsonResponse({'success': False, 'message': '会员姓名不能为空'})
        
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return JsonResponse({'success': False, 'message': '会员不存在'})
        
        # 检查手机号是否被其他会员使用
        if phone and phone != member.phone:
            if Member.objects.filter(phone=phone).exclude(id=member_id).exists():
                return JsonResponse({'success': False, 'message': '该手机号已被其他会员使用'})
        
        try:
            member.name = name
            member.phone = phone
            member.level = level
            member.save()
            return JsonResponse({'success': True, 'message': '会员信息更新成功'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'更新失败：{str(e)}'})
    
    return JsonResponse({'success': False, 'message': '请求方式错误'})


@login_required
@manager_required
def member_delete(request, member_id):
    """
    删除会员
    """
    if request.method == 'POST':
        try:
            member = Member.objects.get(id=member_id)
            member.delete()
            return JsonResponse({'success': True, 'message': '会员删除成功'})
        except Member.DoesNotExist:
            return JsonResponse({'success': False, 'message': '会员不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'删除失败：{str(e)}'})
    
    return JsonResponse({'success': False, 'message': '请求方式错误'})


@login_required
@manager_required
def member_recharge(request):
    """
    会员充值
    """
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        amount = request.POST.get('amount', '0')
        
        if not member_id:
            return JsonResponse({'success': False, 'message': '会员ID不能为空'})
        
        try:
            amount = Decimal(amount)
            if amount == 0:
                return JsonResponse({'success': False, 'message': '充值金额不能等于0'})
            
        except ValueError:
            return JsonResponse({'success': False, 'message': '充值金额格式错误'})
        
        try:
            member = Member.objects.get(id=member_id)

            if amount < 0 and member.balance < abs(amount):
                return JsonResponse({'success': False, 'message': '会员余额不足'})

            member.balance += amount
            member.save()
            return JsonResponse({
                'success': True, 
                'message': f'充值成功，当前余额：¥{member.balance}',
                'balance': member.balance
            })
        except Member.DoesNotExist:
            return JsonResponse({'success': False, 'message': '会员不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'充值失败：{str(e)}'})
    
    return JsonResponse({'success': False, 'message': '请求方式错误'})


@login_required
@manager_required
def member_adjust_points(request):
    """
    调整会员积分
    """
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        points = request.POST.get('points', '0')
        adjust_type = request.POST.get('adjust_type', 'add')  # add 或 subtract
        
        if not member_id:
            return JsonResponse({'success': False, 'message': '会员ID不能为空'})
        
        try:
            points = int(points)
            if points <= 0:
                return JsonResponse({'success': False, 'message': '积分数量必须大于0'})
        except ValueError:
            return JsonResponse({'success': False, 'message': '积分格式错误'})
        
        try:
            member = Member.objects.get(id=member_id)
            
            if adjust_type == 'add':
                member.points += points
            else:
                if member.points < points:
                    return JsonResponse({'success': False, 'message': '积分不足，无法扣除'})
                member.points -= points
            
            member.save()
            return JsonResponse({
                'success': True, 
                'message': f'积分调整成功，当前积分：{member.points}',
                'points': member.points
            })
        except Member.DoesNotExist:
            return JsonResponse({'success': False, 'message': '会员不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'调整失败：{str(e)}'})
    
    return JsonResponse({'success': False, 'message': '请求方式错误'})
