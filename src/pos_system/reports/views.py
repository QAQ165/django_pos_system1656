from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
from django.core.cache import cache
from datetime import timedelta, datetime
from django.db.models import Sum, Count, F, Q

from members.models import Member
from products.models import Product, Category
from sales.models import Order, OrderItem
from users.decorators import manager_required


@login_required
def dashboard(request):
    """
    后台首页仪表盘
    显示系统概览信息，包括今日订单数、销售额、会员数等
    管理员和店长可访问
    """
    try:
        # 检查用户角色权限
        user_role = getattr(request.user, 'role', None)
        if user_role not in ['admin', 'manager']:
            return redirect('sales:pos')
        
        # 会员总数
        total_members = Member.objects.count()
        
        # 商品总数
        total_products = Product.objects.filter(status=True).count()
        
        context = {
            'page_title': '仪表盘',
            'user': request.user,
            'total_members': total_members,
            'total_products': total_products,
        }
        
        # 判断是否为AJAX请求，返回不同模板
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(request, 'reports/dashboard_content.html', context)
        
        return render(request, 'reports/dashboard.html', context)
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect('sales:pos')


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
        return render(request, 'reports/reports_content.html', context)
    
    return render(request, 'reports/reports.html', context)


@login_required
@manager_required
def get_overview_data(request):
    """
    获取经营概览数据
    """
    period = request.GET.get('period', 'day')
    
    cache_key = f'dashboard_overview_{period}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    now = datetime.now()
    if period == 'day':
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'week':
        start_time = now - timedelta(days=now.weekday())
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'month':
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'total':
        start_time = None
        end_time = now
    else:
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    order_query = Q(status='paid')
    if start_time:
        order_query &= Q(create_time__gte=start_time)
    if end_time:
        order_query &= Q(create_time__lte=end_time)
    
    orders = Order.objects.filter(order_query)
    order_count = orders.count()
    total_amount = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    member_orders = orders.filter(member__isnull=False).values('member_id').distinct().count()
    non_member_orders = orders.filter(member__isnull=True).count()
    customer_count = member_orders + non_member_orders
    
    order_items = OrderItem.objects.filter(order__in=orders)
    total_cost = 0
    for item in order_items:
        total_cost += float(item.quantity) * float(item.product.cost)
    
    if total_amount > 0:
        gross_margin = ((float(total_amount) - total_cost) / float(total_amount)) * 100
    else:
        gross_margin = 0
    
    response_data = {
        'code': '1',
        'message': 'success',
        'data': {
            'sales': float(total_amount),
            'orders': order_count,
            'customers': customer_count,
            'gross_margin': round(gross_margin, 2)
        }
    }
    
    cache.set(cache_key, response_data, timeout=60)
    
    return JsonResponse(response_data)


@login_required
@manager_required
def get_trend_data(request):
    """
    获取趋势分析数据
    """
    period = request.GET.get('period', 'day')
    
    cache_key = f'dashboard_trend_{period}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    now = datetime.now()
    if period == 'day':
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        time_points = []
        current = start_time
        hour_interval = 2
        
        while current <= end_time:
            time_points.append(current)
            current += timedelta(hours=hour_interval)
        
        x_axis = [t.strftime('%H:00') for t in time_points]
        
        current_data = []
        for t in time_points:
            next_t = t + timedelta(hours=hour_interval)
            if next_t > end_time:
                next_t = end_time
            
            amount = Order.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t,
                status='paid'
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            current_data.append(float(amount))
        
        last_period_data = []
        for t in time_points:
            last_t = t - timedelta(days=1)
            last_next_t = last_t + timedelta(hours=hour_interval)
            
            amount = Order.objects.filter(
                create_time__gte=last_t,
                create_time__lt=last_next_t,
                status='paid'
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            last_period_data.append(float(amount))
            
    elif period == 'week':
        start_time = now - timedelta(days=now.weekday())
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
        
        time_points = []
        current = start_time
        
        while current <= end_time:
            time_points.append(current)
            current += timedelta(days=1)
        
        x_axis = [t.strftime('%m-%d') for t in time_points]
        
        current_data = []
        for t in time_points:
            next_t = t + timedelta(days=1)
            if next_t > end_time:
                next_t = end_time
            
            amount = Order.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t,
                status='paid'
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            current_data.append(float(amount))
        
        last_period_data = []
        for t in time_points:
            last_t = t - timedelta(weeks=1)
            last_next_t = last_t + timedelta(days=1)
            
            amount = Order.objects.filter(
                create_time__gte=last_t,
                create_time__lt=last_next_t,
                status='paid'
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            last_period_data.append(float(amount))
            
    elif period == 'month':
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = now
        
        time_points = []
        current = start_time
        day_interval = 1 if now.day < 15 else 2
        
        while current <= end_time:
            time_points.append(current)
            current += timedelta(days=day_interval)
        
        x_axis = [t.strftime('%m-%d') for t in time_points]
        
        current_data = []
        for t in time_points:
            next_t = t + timedelta(days=day_interval)
            if next_t > end_time:
                next_t = end_time
            
            amount = Order.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t,
                status='paid'
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            current_data.append(float(amount))
        
        last_period_data = []
        for t in time_points:
            last_t = t - timedelta(days=30)
            last_next_t = last_t + timedelta(days=day_interval)
            
            amount = Order.objects.filter(
                create_time__gte=last_t,
                create_time__lt=last_next_t,
                status='paid'
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            last_period_data.append(float(amount))
            
    elif period == 'total':
        end_time = now
        start_time = now - timedelta(days=365)
        
        time_points = []
        current = start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        while current <= end_time:
            time_points.append(current)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        x_axis = [t.strftime('%Y-%m') for t in time_points]
        
        current_data = []
        for i, t in enumerate(time_points):
            if i < len(time_points) - 1:
                next_t = time_points[i + 1]
            else:
                next_t = end_time
            
            amount = Order.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t,
                status='paid'
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            current_data.append(float(amount))
        
        last_period_data = []
    else:
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
        x_axis = ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00']
        current_data = [0] * 8
        last_period_data = [0] * 8
    
    response_data = {
        'code': '1',
        'message': 'success',
        'data': {
            'x_axis': x_axis,
            'current_data': current_data,
            'last_period_data': last_period_data
        }
    }
    
    cache.set(cache_key, response_data, timeout=60)
    
    return JsonResponse(response_data)


@login_required
@manager_required
def get_hot_products(request):
    """
    获取热销商品数据
    """
    period = request.GET.get('period', 'day')
    
    cache_key = f'dashboard_hot_products_{period}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    now = datetime.now()
    if period == 'day':
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'week':
        start_time = now - timedelta(days=now.weekday())
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'month':
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'total':
        start_time = None
        end_time = now
    else:
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    order_query = Q(order__status='paid')
    if start_time:
        order_query &= Q(order__create_time__gte=start_time)
    if end_time:
        order_query &= Q(order__create_time__lte=end_time)
    
    hot_products = OrderItem.objects.filter(order_query)\
        .values('product__name')\
        .annotate(total_quantity=Sum('quantity'))\
        .order_by('-total_quantity')[:10]
    
    product_names = [p['product__name'] for p in hot_products]
    quantities = [p['total_quantity'] for p in hot_products]
    
    response_data = {
        'code': '1',
        'message': 'success',
        'data': {
            'product_names': product_names,
            'quantities': quantities
        }
    }
    
    cache.set(cache_key, response_data, timeout=60)
    
    return JsonResponse(response_data)


@login_required
@manager_required
def get_sales_rank(request):
    """
    获取商品销量排行数据（只统计一级分类）
    """
    period = request.GET.get('period', 'day')
    
    cache_key = f'dashboard_sales_rank_{period}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    now = datetime.now()
    if period == 'day':
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'week':
        start_time = now - timedelta(days=now.weekday())
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'month':
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'total':
        start_time = None
        end_time = now
    else:
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    order_query = Q(order__status='paid')
    if start_time:
        order_query &= Q(order__create_time__gte=start_time)
    if end_time:
        order_query &= Q(order__create_time__lte=end_time)
    
    sales_rank = OrderItem.objects.filter(order_query)\
        .values('product__category__name')\
        .annotate(total_quantity=Sum('quantity'))\
        .order_by('-total_quantity')
    
    categories = [r['product__category__name'] for r in sales_rank]
    quantities = [r['total_quantity'] for r in sales_rank]
    
    response_data = {
        'code': '1',
        'message': 'success',
        'data': {
            'categories': categories,
            'quantities': quantities
        }
    }
    
    cache.set(cache_key, response_data, timeout=60)
    
    return JsonResponse(response_data)


@login_required
@manager_required
def get_profit_rank(request):
    """
    获取毛利排行数据（只统计一级分类）
    """
    period = request.GET.get('period', 'day')
    
    cache_key = f'dashboard_profit_rank_{period}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    now = datetime.now()
    if period == 'day':
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'week':
        start_time = now - timedelta(days=now.weekday())
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'month':
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'total':
        start_time = None
        end_time = now
    else:
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    order_query = Q(order__status='paid')
    if start_time:
        order_query &= Q(order__create_time__gte=start_time)
    if end_time:
        order_query &= Q(order__create_time__lte=end_time)
    
    order_items = OrderItem.objects.filter(order_query)
    category_profits = {}
    
    for item in order_items:
        category_name = item.product.category.name
        profit = (float(item.price) - float(item.product.cost)) * item.quantity
        
        if category_name in category_profits:
            category_profits[category_name] += profit
        else:
            category_profits[category_name] = profit
    
    sorted_profits = sorted(category_profits.items(), key=lambda x: x[1], reverse=True)
    
    categories = [c[0] for c in sorted_profits]
    profits = [round(c[1], 2) for c in sorted_profits]
    
    response_data = {
        'code': '1',
        'message': 'success',
        'data': {
            'categories': categories,
            'profits': profits
        }
    }
    
    cache.set(cache_key, response_data, timeout=60)
    
    return JsonResponse(response_data)


@login_required
@manager_required
def get_member_consumption(request):
    """
    获取会员消费占比数据
    """
    period = request.GET.get('period', 'day')
    
    cache_key = f'dashboard_member_consumption_{period}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    now = datetime.now()
    if period == 'day':
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'week':
        start_time = now - timedelta(days=now.weekday())
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'month':
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif period == 'total':
        start_time = None
        end_time = now
    else:
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    order_query = Q(status='paid')
    if start_time:
        order_query &= Q(create_time__gte=start_time)
    if end_time:
        order_query &= Q(create_time__lte=end_time)
    
    member_orders = Order.objects.filter(order_query, member__isnull=False).count()
    non_member_orders = Order.objects.filter(order_query, member__isnull=True).count()
    
    response_data = {
        'code': '1',
        'message': 'success',
        'data': {
            'member_orders': member_orders,
            'non_member_orders': non_member_orders
        }
    }
    
    cache.set(cache_key, response_data, timeout=60)
    
    return JsonResponse(response_data)


@login_required
@manager_required
def get_new_members(request):
    """
    获取新增会员数数据
    """
    period = request.GET.get('period', 'day')
    
    cache_key = f'dashboard_new_members_{period}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    now = datetime.now()
    if period == 'day':
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        time_points = []
        current = start_time
        hour_interval = 2
        
        while current <= end_time:
            time_points.append(current)
            current += timedelta(hours=hour_interval)
        
        x_axis = [t.strftime('%H:00') for t in time_points]
        
        new_members = []
        for t in time_points:
            next_t = t + timedelta(hours=hour_interval)
            if next_t > end_time:
                next_t = end_time
            
            count = Member.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t
            ).count()
            new_members.append(count)
            
    elif period == 'week':
        start_time = now - timedelta(days=now.weekday())
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
        
        time_points = []
        current = start_time
        
        while current <= end_time:
            time_points.append(current)
            current += timedelta(days=1)
        
        x_axis = [t.strftime('%m-%d') for t in time_points]
        
        new_members = []
        for t in time_points:
            next_t = t + timedelta(days=1)
            if next_t > end_time:
                next_t = end_time
            
            count = Member.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t
            ).count()
            new_members.append(count)
            
    elif period == 'month':
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = now
        
        time_points = []
        current = start_time
        day_interval = 1 if now.day < 15 else 2
        
        while current <= end_time:
            time_points.append(current)
            current += timedelta(days=day_interval)
        
        x_axis = [t.strftime('%m-%d') for t in time_points]
        
        new_members = []
        for t in time_points:
            next_t = t + timedelta(days=day_interval)
            if next_t > end_time:
                next_t = end_time
            
            count = Member.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t
            ).count()
            new_members.append(count)
            
    elif period == 'total':
        end_time = now
        start_time = now - timedelta(days=365)
        
        time_points = []
        current = start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        while current <= end_time:
            time_points.append(current)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        x_axis = [t.strftime('%Y-%m') for t in time_points]
        
        new_members = []
        for i, t in enumerate(time_points):
            if i < len(time_points) - 1:
                next_t = time_points[i + 1]
            else:
                next_t = end_time
            
            count = Member.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t
            ).count()
            new_members.append(count)
    else:
        x_axis = ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00']
        new_members = [0] * 8
    
    response_data = {
        'code': '1',
        'message': 'success',
        'data': {
            'x_axis': x_axis,
            'new_members': new_members
        }
    }
    
    cache.set(cache_key, response_data, timeout=60)
    
    return JsonResponse(response_data)


@login_required
@manager_required
def get_repurchase_rate(request):
    """
    获取会员复购率数据
    复购率：当前时间内新增的会员购买次数大于2的会员数量
    """
    period = request.GET.get('period', 'day')
    
    # 计算时间范围
    now = datetime.now()
    if period == 'day':
        # 昨日数据，按小时统计
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # 生成时间点
        time_points = []
        current = start_time
        hour_interval = 2  # 昨日数据固定间隔2小时
        
        while current <= end_time:
            time_points.append(current)
            current += timedelta(hours=hour_interval)
        
        # 生成x轴标签
        x_axis = [t.strftime('%H:00') for t in time_points]
        
        # 统计每个时间点的复购率
        repurchase_rate = []
        for t in time_points:
            next_t = t + timedelta(hours=hour_interval)
            if next_t > end_time:
                next_t = end_time
            
            # 获取该时间范围内的新增会员
            new_members = Member.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t
            )
            new_member_ids = [m.id for m in new_members]
            
            # 统计这些会员的购买次数
            member_orders = Order.objects.filter(
                member_id__in=new_member_ids,
                status='paid'
            ).values('member_id').annotate(order_count=Count('id'))
            
            # 计算复购率（购买次数大于2的会员数量）
            repurchase_members = [m for m in member_orders if m['order_count'] > 2]
            rate = len(repurchase_members) / len(new_members) * 100 if new_members else 0
            repurchase_rate.append(round(rate, 2))
            
    elif period == 'week':
        # 本周数据，按天统计
        start_time = now - timedelta(days=now.weekday())
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
        
        # 生成时间点
        time_points = []
        current = start_time
        
        while current <= end_time:
            time_points.append(current)
            current += timedelta(days=1)
        
        # 生成x轴标签
        x_axis = [t.strftime('%m-%d') for t in time_points]
        
        # 统计每天的复购率
        repurchase_rate = []
        for t in time_points:
            next_t = t + timedelta(days=1)
            if next_t > end_time:
                next_t = end_time
            
            # 获取该时间范围内的新增会员
            new_members = Member.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t
            )
            new_member_ids = [m.id for m in new_members]
            
            # 统计这些会员的购买次数
            member_orders = Order.objects.filter(
                member_id__in=new_member_ids,
                status='paid'
            ).values('member_id').annotate(order_count=Count('id'))
            
            # 计算复购率（购买次数大于2的会员数量）
            repurchase_members = [m for m in member_orders if m['order_count'] > 2]
            rate = len(repurchase_members) / len(new_members) * 100 if new_members else 0
            repurchase_rate.append(round(rate, 2))
            
    elif period == 'month':
        # 本月数据，按天统计
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = now
        
        # 生成时间点
        time_points = []
        current = start_time
        day_interval = 1 if now.day < 15 else 2
        
        while current <= end_time:
            time_points.append(current)
            current += timedelta(days=day_interval)
        
        # 生成x轴标签
        x_axis = [t.strftime('%m-%d') for t in time_points]
        
        # 统计每天的复购率
        repurchase_rate = []
        for t in time_points:
            next_t = t + timedelta(days=day_interval)
            if next_t > end_time:
                next_t = end_time
            
            # 获取该时间范围内的新增会员
            new_members = Member.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t
            )
            new_member_ids = [m.id for m in new_members]
            
            # 统计这些会员的购买次数
            member_orders = Order.objects.filter(
                member_id__in=new_member_ids,
                status='paid'
            ).values('member_id').annotate(order_count=Count('id'))
            
            # 计算复购率（购买次数大于2的会员数量）
            repurchase_members = [m for m in member_orders if m['order_count'] > 2]
            rate = len(repurchase_members) / len(new_members) * 100 if new_members else 0
            repurchase_rate.append(round(rate, 2))
            
    elif period == 'total':
        # 累计数据，过去12个月
        end_time = now
        start_time = now - timedelta(days=365)
        
        # 生成时间点（每月1号）
        time_points = []
        current = start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        while current <= end_time:
            time_points.append(current)
            # 移到下个月1号
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        # 生成x轴标签
        x_axis = [t.strftime('%Y-%m') for t in time_points]
        
        # 统计每月的复购率
        repurchase_rate = []
        for i, t in enumerate(time_points):
            if i < len(time_points) - 1:
                next_t = time_points[i + 1]
            else:
                next_t = end_time
            
            # 获取该时间范围内的新增会员
            new_members = Member.objects.filter(
                create_time__gte=t,
                create_time__lt=next_t
            )
            new_member_ids = [m.id for m in new_members]
            
            # 统计这些会员的购买次数
            member_orders = Order.objects.filter(
                member_id__in=new_member_ids,
                status='paid'
            ).values('member_id').annotate(order_count=Count('id'))
            
            # 计算复购率（购买次数大于2的会员数量）
            repurchase_members = [m for m in member_orders if m['order_count'] > 2]
            rate = len(repurchase_members) / len(new_members) * 100 if new_members else 0
            repurchase_rate.append(round(rate, 2))
    else:
        # 默认返回当天数据
        x_axis = ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00']
        repurchase_rate = [0] * 8
    
    return JsonResponse({
        'code': '1',
        'message': 'success',
        'data': {
            'x_axis': x_axis,
            'repurchase_rate': repurchase_rate
        }
    })


@login_required
@manager_required
def get_dashboard_sales_trend(request):
    """
    获取仪表盘销售趋势数据（今日）
    """
    now = datetime.now()
    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = now
    
    # 生成时间点
    time_points = []
    current = start_time
    
    # 12点前每小时统计，12点后每2小时统计
    while current <= end_time:
        time_points.append(current)
        # 根据时间设置间隔
        if now.hour < 12:
            current += timedelta(hours=1)
        else:
            current += timedelta(hours=2)
    
    # 生成x轴标签
    x_axis = [t.strftime('%H:00') for t in time_points]
    
    # 生成当天数据
    sales_data = []
    for i, t in enumerate(time_points):
        # 计算下一个时间点
        if i < len(time_points) - 1:
            next_t = time_points[i + 1]
        else:
            next_t = end_time
        
        amount = Order.objects.filter(
            create_time__gte=t,
            create_time__lt=next_t,
            status='paid'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        sales_data.append(float(amount))
    
    return JsonResponse({
        'code': '1',
        'message': 'success',
        'data': {
            'x_axis': x_axis,
            'sales_data': sales_data
        }
    })


@login_required
@manager_required
def get_dashboard_sales_rank(request):
    """
    获取仪表盘销售占比数据（今日，只统计一级分类）
    """
    now = datetime.now()
    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = now
    
    # 构建查询条件
    order_query = Q(order__status='paid') & Q(order__create_time__gte=start_time) & Q(order__create_time__lte=end_time)
    
    # 统计一级分类销量
    sales_rank = OrderItem.objects.filter(order_query)\
        .values('product__category__name')\
        .annotate(total_quantity=Sum('quantity'))\
        .order_by('-total_quantity')
    
    # 提取数据
    categories = [r['product__category__name'] for r in sales_rank]
    quantities = [r['total_quantity'] for r in sales_rank]
    
    return JsonResponse({
        'code': '1',
        'message': 'success',
        'data': {
            'categories': categories,
            'quantities': quantities
        }
    })


@login_required
@manager_required
def get_dashboard_stock_warning(request):
    """
    获取库存预警数据（5条，按库存量增序）
    """
    # 查询库存低于预警值的商品，按库存量增序排列，取前5条
    low_stock_products = Product.objects.filter(
        stock__lte=models.F('warning_stock')
    ).order_by('stock')[:5]
    
    # 提取数据
    products_data = []
    for product in low_stock_products:
        products_data.append({
            'id': product.id,
            'name': product.name,
            'stock': product.stock,
            'warning_stock': product.warning_stock,
            'unit': product.unit
        })
    
    return JsonResponse({
        'code': '1',
        'message': 'success',
        'data': {
            'products': products_data
        }
    })


@login_required
@manager_required
def get_dashboard_recent_orders(request):
    """
    获取最近订单数据（5条）
    """
    # 查询最近5条已支付订单
    recent_orders = Order.objects.filter(
        status='paid'
    ).order_by('-create_time')[:5]
    
    # 提取数据
    orders_data = []
    for order in recent_orders:
        orders_data.append({
            'order_no': order.order_no,
            'total_amount': float(order.total_amount),
            'payment_method': order.get_payment_method_display(),
            'create_time': order.create_time.strftime('%H:%M:%S')
        })
    
    return JsonResponse({
        'code': '1',
        'message': 'success',
        'data': {
            'orders': orders_data
        }
    })


@login_required
@manager_required
def get_dashboard_expiry_warning(request):
    """
    获取过期提醒数据（一个月内就要过期的商品）
    """
    from products.models import StockLog
    
    # 计算一个月后的日期
    now = datetime.now()
    one_month_later = now + timedelta(days=30)
    
    # 查询一个月内就要过期的商品，按过期时间升序排序
    expiry_products = Product.objects.filter(
        expiry_date__isnull=False,
        expiry_date__lte=one_month_later,
        stock__gt=0  # 只显示有库存的商品
    ).order_by('expiry_date')
    
    # 提取数据
    products_data = []
    for product in expiry_products:
        # 获取最近入库时间
        last_stock_log = StockLog.objects.filter(
            product=product,
            change_type__in=['purchase', 'return']
        ).order_by('-create_time').first()
        
        last_stock_time = last_stock_log.create_time.strftime('%Y-%m-%d %H:%M') if last_stock_log else '无'
        
        products_data.append({
            'id': product.id,
            'name': product.name,
            'expiry_date': product.expiry_date.strftime('%Y-%m-%d %H:%M'),
            'stock': product.stock,
            'last_stock_time': last_stock_time
        })
    
    return JsonResponse({
        'code': '1',
        'message': 'success',
        'data': {
            'products': products_data
        }
    })


