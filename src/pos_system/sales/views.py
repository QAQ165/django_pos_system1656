from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.db import transaction
from django.core.cache import cache
from datetime import datetime
import json

from dist.POS系统._internal.django.contrib.gis.measure import D
from .models import Order, OrderItem, SuspendedCart
from users.models import User
from members.models import Member
from products.models import Product, StockLog
from system.models import SystemConfig
from decimal import Decimal



@login_required
def pos_view(request):
    """
    收银台页面（POS）
    收银员的主要工作界面
    """
    # 检查用户角色，只有收银员和管理员可以访问
    if request.user.role not in ['cashier', 'admin', 'manager']:
        return redirect('dashboard')
    
    return render(request, 'sales/pos.html', {
        'user': request.user
    })


@login_required
def order_list(request):
    """
    订单管理页面
    展示订单列表，支持筛选和分页
    """
    # 获取筛选参数
    order_no = request.GET.get('order_no', '')
    status = request.GET.get('status', '')
    payment_method = request.GET.get('payment_method', '')
    cashier_search = request.GET.get('cashier', '')
    member_phone = request.GET.get('member_phone', '')
    product_name = request.GET.get('product_name', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    page = request.GET.get('page', 1)
    
    # 基础查询 - 预加载关联数据
    orders = Order.objects.select_related('cashier', 'member').prefetch_related('items', 'items__product').order_by('-create_time')
    
    # 按订单号筛选
    if order_no:
        orders = orders.filter(order_no__icontains=order_no)
    
    # 按状态筛选
    if status:
        orders = orders.filter(status=status)
    
    # 按支付方式筛选
    if payment_method:
        orders = orders.filter(payment_method=payment_method)
    
    # 按收银员名称筛选
    if cashier_search:
        orders = orders.filter(cashier__username__icontains=cashier_search)
    
    # 按会员手机号筛选
    if member_phone:
        orders = orders.filter(member__phone__icontains=member_phone)
    
    # 按商品名称筛选
    if product_name:
        orders = orders.filter(items__product__name__icontains=product_name).distinct()
    
    # 按时间区间筛选
    if start_date:
        orders = orders.filter(create_time__date__gte=start_date)
    if end_date:
        orders = orders.filter(create_time__date__lte=end_date)
    
    # 分页
    paginator = Paginator(orders, 20)
    orders_page = paginator.get_page(page)
    
    # 获取所有收银员用于筛选下拉框
    cashiers = User.objects.filter(role__in=['cashier', 'admin', 'manager']).values('id', 'username')
    
    context = {
        'orders': orders_page,
        'cashiers': cashiers,
        'order_no': order_no,
        'status_filter': status,
        'payment_method_filter': payment_method,
        'cashier_search': cashier_search,
        'member_phone': member_phone,
        'product_name': product_name,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    # 判断是否为AJAX请求
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'sales/order_list_content.html', context)
    
    return render(request, 'sales/order_list.html', context)


@login_required
def api_suspend_order(request):
    """
    挂单API接口
    将当前购物车商品信息保存到SuspendedCart表
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方式错误'})
    
    try:
        cart_items = json.loads(request.POST.get('cart_items', '[]'))
        member_id = request.POST.get('member_id')
        note = request.POST.get('note', '')
        
        if not cart_items:
            return JsonResponse({'success': False, 'message': '购物车为空'})
        
        # 创建挂单记录
        suspended_cart = SuspendedCart.objects.create(
            cashier=request.user,
            cart_data={
                'cart_items': cart_items,
                'member_id': member_id,
                'discount_amount': float(request.POST.get('discount_amount', 0))
            },
            note=note
        )
        
        return JsonResponse({
            'success': True,
            'message': '挂单成功',
            'order_id': suspended_cart.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'挂单失败：{str(e)}'})


@login_required
def api_get_suspended_orders(request):
    """
    获取当前收银员的所有挂单列表
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '请求方式错误'})
    
    try:
        # 获取当前收银员的所有挂单中状态，按创建时间倒序
        suspended_carts = SuspendedCart.objects.filter(
            cashier=request.user,
            status=1  # 只显示挂单中的订单
        ).order_by('-create_time')
        
        data = []
        for cart in suspended_carts:
            cart_data = cart.cart_data
            cart_items = cart_data.get('cart_items', [])
            
            # 格式化创建时间
            create_time = cart.create_time.strftime('%Y-%m-%d %H:%M:%S')
            
            data.append({
                'id': cart.id,
                'order_no': f'SUS{cart.id:06d}',
                'create_time': create_time,
                'cart_data': cart_items,
                'note': cart.note
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'获取挂单失败：{str(e)}'})


@login_required
def api_resume_order(request):
    """
    取单API接口
    从SuspendedCart表中恢复挂单信息，并删除该挂单记录
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方式错误'})
    
    try:
        order_id = request.POST.get('order_id')
        
        if not order_id:
            return JsonResponse({'success': False, 'message': '订单ID不能为空'})
        
        # 获取挂单记录
        try:
            suspended_cart = SuspendedCart.objects.get(
                id=order_id,
                cashier=request.user
            )
        except SuspendedCart.DoesNotExist:
            return JsonResponse({'success': False, 'message': '挂单不存在或已被删除'})
        
        # 获取挂单数据
        cart_data = suspended_cart.cart_data
        cart_items = cart_data.get('cart_items', [])
        member_id = cart_data.get('member_id')
        discount_amount = cart_data.get('discount_amount', 0)
        
        # 获取会员信息
        member = None
        if member_id:
            try:
                member_obj = Member.objects.get(id=member_id)
                member = {
                    'id': member_obj.id,
                    'card_no': member_obj.card_no,
                    'name': member_obj.name,
                    'phone': member_obj.phone,
                    'level': member_obj.level,
                    'balance': float(member_obj.balance),
                    'points': member_obj.points
                }
            except Member.DoesNotExist:
                pass
        
        # 更新挂单状态为已取单
        suspended_cart.status = 2
        suspended_cart.save()
        
        return JsonResponse({
            'success': True,
            'message': '取单成功',
            'data': {
                'cart_items': cart_items,
                'member': member,
                'discount_amount': discount_amount
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'取单失败：{str(e)}'})


@login_required
def api_checkout(request):
    """
    结算API接口
    保存订单信息到订单表和订单明细表，扣减库存，记录库存日志
    如果是会员支付，扣减会员余额并增加积分
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方式错误'})
    
    user_id = request.user.id
    lock_key = f'checkout_lock_{user_id}'
    
    if cache.get(lock_key):
        return JsonResponse({'success': False, 'message': '正在处理中，请勿重复提交'})
    
    cache.set(lock_key, True, timeout=30)
    
    try:
        cart_items = json.loads(request.POST.get('cart_items', '[]'))
        member_id = request.POST.get('member_id')
        payment_method = request.POST.get('payment_method')
        discount_amount = Decimal(request.POST.get('discount_amount', 0))
        
        if not cart_items:
            return JsonResponse({'success': False, 'message': '购物车为空'})
        
        if payment_method not in ['cash', 'wechat', 'alipay', 'member']:
            return JsonResponse({'success': False, 'message': '支付方式无效'})
        
        if payment_method == 'member' and not member_id:
            return JsonResponse({'success': False, 'message': '会员支付需要选择会员'})
        
        # 计算订单总额
        total_amount = Decimal(sum(item.get('total', 0) for item in cart_items))
        paid_amount = total_amount - discount_amount
        
        # 获取会员
        member = None
        if member_id:
            try:
                member = Member.objects.get(id=member_id)
            except Member.DoesNotExist:
                return JsonResponse({'success': False, 'message': '会员不存在'})
        
        # 如果是会员支付，检查余额是否足够
        if payment_method == 'member' and member and member.balance < paid_amount:
            return JsonResponse({'success': False, 'message': '会员余额不足'})
        
        # 使用数据库事务确保所有操作要么全部成功，要么全部回滚
        with transaction.atomic():
            # 生成订单号
            order_no = generate_order_no()
            
            # 创建订单
            order = Order.objects.create(
                order_no=order_no,
                cashier=request.user,
                member=member,
                total_amount=total_amount,
                paid_amount=paid_amount,
                change_amount=0.00,
                payment_method=payment_method,
                status='paid'
            )
            
            # 创建订单明细并扣减库存
            for item in cart_items:
                product_id = item.get('id')
                quantity = int(item.get('quantity', 0))
                price = Decimal(item.get('price', 0))
                subtotal = Decimal(item.get('total', 0))
                
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    raise Exception(f'商品不存在')
                
                # 检查库存是否足够
                if product.stock < quantity:
                    raise Exception(f'商品 {product.name} 库存不足')
                
                # 创建订单明细
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price,
                    subtotal=subtotal
                )
                
                # 扣减库存
                before_stock = product.stock
                after_stock = before_stock - quantity
                product.stock = after_stock
                product.save()
                
                # 记录库存日志
                StockLog.objects.create(
                    product=product,
                    change_type='sale',
                    quantity=quantity,
                    before_stock=before_stock,
                    after_stock=after_stock,
                    order=order,
                    operator=request.user
                )
            
            # 如果是会员支付，扣减余额并增加积分
            if payment_method == 'member' and member:
                member.balance -= paid_amount
                member.points += int(paid_amount)
                member.last_visit_time = datetime.now()
                member.save()
            
            # 检查是否需要赠送积分（满额赠送）
            if member:
                # 获取系统配置
                config = SystemConfig.get_config()
                threshold_amount = config.threshold_amount
                reward_points = config.reward_points
                
                # 检查条件：阈值和赠送积分都大于0
                if threshold_amount > 0 and reward_points > 0:
                    reward_count = int(paid_amount // Decimal(str(threshold_amount)))
                    if reward_count > 0:
                        total_reward = reward_count * reward_points
                        member.points += total_reward
                        member.save()
        
        return JsonResponse({
            'success': True,
            'message': '结算成功',
            'data': {
                'order_no': order_no,
                'total_amount': total_amount,
                'paid_amount': paid_amount
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'结算失败：{str(e)}'})
    finally:
        cache.delete(lock_key)


def generate_order_no():
    """
    生成订单号
    格式：ORD + 年月日时分秒 + 4位随机数
    """
    from django.utils import timezone
    import random
    
    now = datetime.now()
    date_str = now.strftime('%Y%m%d%H%M%S')
    random_str = str(random.randint(1000, 9999))
    return f'ORD{date_str}{random_str}'