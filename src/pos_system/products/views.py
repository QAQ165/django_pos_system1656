from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.contrib.auth.decorators import login_required
import os
import time
import random
import string
from django.conf import settings
import openpyxl

from products.models import Category, Product, StockLog
from users.decorators import manager_required


@login_required
@manager_required
def admin_product_categories(request):
    """
    商品分类管理页面
    管理员和店长可访问
    """
    # 获取筛选参数
    level_filter = request.GET.get('level', '')
    search_query = request.GET.get('search', '')
    
    # 基础查询
    categories = Category.objects.all().order_by('level', 'sort_order', 'id')
    
    # 按级别筛选
    if level_filter:
        categories = categories.filter(level=level_filter)
    
    # 按名称搜索
    if search_query:
        categories = categories.filter(name__icontains=search_query)
    
    context = {
        'page_title': '商品分类',
        'user': request.user,
        'categories': categories,
        'level_filter': level_filter,
        'search_query': search_query,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'products/product_categories_content.html', context)
    
    return render(request, 'products/product_categories.html', context)


@login_required
@manager_required
def admin_product_list(request):
    """
    商品列表页面
    管理员和店长可访问
    """
    # 获取筛选参数
    page = request.GET.get('page', 1)
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    category_search = request.GET.get('category_search', '')
    search_query = request.GET.get('search', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # 基础查询
    products = Product.objects.all().order_by('-create_time')
    
    # 筛选上架状态
    if status_filter:
        products = products.filter(status=status_filter == '1')
    
    # 通过分类名称搜索分类，再筛选商品
    if category_search:
        category_ids = Category.objects.filter(name__icontains=category_search).values_list('id', flat=True)
        products = products.filter(category_id__in=category_ids)
    
    # 直接通过分类ID筛选
    if category_filter:
        try:
            category = Category.objects.get(id=category_filter)
            products = products.filter(category=category)
        except Category.DoesNotExist:
            pass
    
    # 搜索商品名称、条码
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(barcode__icontains=search_query)
        )
    
    # 按创建时间筛选
    if start_date:
        from datetime import datetime
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        products = products.filter(create_time__gte=start_datetime)
    
    if end_date:
        from datetime import datetime, timedelta
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
        end_datetime = end_datetime + timedelta(days=1)
        products = products.filter(create_time__lt=end_datetime)
    
    # 分页
    paginator = Paginator(products, 20)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # 获取所有分类用于筛选下拉框
    all_categories = Category.objects.all().order_by('level', 'sort_order', 'id')
  
    template_name = 'products/product_list.html'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        template_name = 'products/product_list_content.html'
    # print(template_name)
    return render(request, template_name, {
        'page_title': '商品列表',
        'user': request.user,
        'products': products,
        'all_categories': all_categories,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'category_search': category_search,
        'search_query': search_query,
        'start_date': start_date,
        'end_date': end_date,
        'template_name': template_name,
    })


def handle_uploaded_image(image_file):
    """
    处理上传的图片文件
    使用时间戳和随机字符串生成文件名，保存到media/products目录
    """
    if not image_file:
        return None
    
    # 生成文件名：时间戳_随机字符串.扩展名
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    ext = os.path.splitext(image_file.name)[1].lower()
    
    # 确保扩展名合法
    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        ext = '.jpg'
    
    filename = f"{timestamp}_{random_str}{ext}"
    
    # 确保目录存在
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'products')
    os.makedirs(upload_dir, exist_ok=True)
    
    # 保存文件
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, 'wb+') as destination:
        for chunk in image_file.chunks():
            destination.write(chunk)
    
    # 返回相对路径（用于数据库存储）
    return f"products/{filename}"


@login_required
@manager_required
def admin_product_add(request, product_id=None):
    """
    新增/编辑商品页面
    管理员和店长可访问
    如果有product_id参数，则为编辑模式；否则为新增模式
    """
    # 判断是否为编辑模式
    product = None
    if product_id:
        product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        # 处理表单提交
        barcode = request.POST.get('barcode', '').strip()
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        cost = request.POST.get('cost', '0.00')
        stock = request.POST.get('stock', '0')
        warning_stock = request.POST.get('warning_stock', '5')
        unit = request.POST.get('unit', '件')
        status = request.POST.get('status') == '1'
        expiry_date = request.POST.get('expiry_date')
        shelf_life = request.POST.get('shelf_life')
        
        # 验证必填字段
        if not name or not category_id or not price:
            context = {
                'page_title': '编辑商品' if product else '新增商品',
                'user': request.user,
                'all_categories': Category.objects.all().order_by('level', 'sort_order', 'id'),
                'error': '商品名称、分类和零售价为必填项',
                'form_data': request.POST,
                'product': product,
            }
            return render(request, 'products/product_add.html', context)
        
        try:
            # 处理图片上传
            image_path = None
            if 'image' in request.FILES:
                image_file = request.FILES['image']
                if image_file:
                    image_path = handle_uploaded_image(image_file)
            
            category = Category.objects.get(id=category_id)
            
            if product:
                # 编辑模式：更新商品
                old_stock = product.stock
                product.barcode = barcode if barcode else None
                product.name = name
                product.category = category
                product.price = price
                product.cost = cost
                product.stock = int(stock)
                product.warning_stock = int(warning_stock)
                product.unit = unit
                product.status = status
                
                # 处理过期时间
                if expiry_date:
                    from datetime import datetime
                    try:
                        expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M')
                        product.expiry_date = expiry_datetime
                    except:
                        pass
                else:
                    product.expiry_date = None
                
                # 处理保质期
                if shelf_life:
                    try:
                        product.shelf_life = int(shelf_life)
                    except:
                        product.shelf_life = None
                else:
                    product.shelf_life = None
                
                # 如果有新图片，更新图片路径
                if image_path:
                    # 删除旧图片
                    if product.image:
                        old_image_path = os.path.join(settings.MEDIA_ROOT, str(product.image))
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    product.image = image_path
                
                product.save()
                
                # 记录库存变动日志（如果库存有变化）
                stock_change = int(stock) - old_stock
                if stock_change != 0:
                    change_type = 'purchase' if stock_change > 0 else 'adjust'
                    StockLog.objects.create(
                        product=product,
                        change_type=change_type,
                        quantity=abs(stock_change),
                        before_stock=old_stock,
                        after_stock=int(stock),
                        operator=request.user
                    )
                
                success_message = '商品更新成功'
            else:
                # 新增模式：创建商品
                # 处理过期时间
                expiry_datetime = None
                if expiry_date:
                    from datetime import datetime
                    try:
                        expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M')
                    except:
                        pass
                
                # 处理保质期
                shelf_life_value = None
                if shelf_life:
                    try:
                        shelf_life_value = int(shelf_life)
                    except:
                        pass
                
                product = Product.objects.create(
                    barcode=barcode if barcode else None,
                    name=name,
                    category=category,
                    price=price,
                    cost=cost,
                    stock=int(stock),
                    warning_stock=int(warning_stock),
                    unit=unit,
                    status=status,
                    expiry_date=expiry_datetime,
                    shelf_life=shelf_life_value,
                    image=image_path
                )
                
                # 记录库存日志（如果有库存）
                if int(stock) > 0:
                    StockLog.objects.create(
                        product=product,
                        change_type='purchase',
                        quantity=int(stock),
                        before_stock=0,
                        after_stock=int(stock),
                        operator=request.user
                    )
                
                success_message = '商品创建成功'
            
            # 重定向到商品列表
            return redirect('products:product_list')
            
        except Exception as e:
            context = {
                'page_title': '编辑商品' if product else '新增商品',
                'user': request.user,
                'all_categories': Category.objects.all().order_by('level', 'sort_order', 'id'),
                'error': f'{"更新" if product else "创建"}商品失败：{str(e)}',
                'form_data': request.POST,
                'product': product,
            }
            return render(request, 'products/product_add.html', context)
    
    # GET请求：显示表单
    context = {
        'page_title': '编辑商品' if product else '新增商品',
        'user': request.user,
        'all_categories': Category.objects.all().order_by('level', 'sort_order', 'id'),
        'product': product,
    }
    
    return render(request, 'products/product_add.html', context)


@login_required
@manager_required
def admin_product_delete(request, product_id):
    """
    删除商品
    管理员和店长可访问
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方式错误'})
    
    product = get_object_or_404(Product, id=product_id)
    
    try:
        # 删除商品图片文件
        if product.image:
            image_path = os.path.join(settings.MEDIA_ROOT, str(product.image))
            if os.path.exists(image_path):
                os.remove(image_path)
        
        # 删除商品（关联的库存日志会自动处理，根据模型on_delete设置）
        product.delete()
        
        return JsonResponse({'success': True, 'message': '商品删除成功'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败：{str(e)}'})


def get_all_child_categories(parent_category):
    """
    递归获取所有子分类ID（包括所有子级）
    """
    child_ids = []
    direct_children = Category.objects.filter(parent=parent_category)
    for child in direct_children:
        child_ids.append(child.id)
        child_ids.extend(get_all_child_categories(child))
    return child_ids


@login_required
@manager_required
def admin_category_add(request):
    """
    新增分类页面
    管理员和店长可访问
    """
    # 获取所有分类用于父分类选择
    all_categories = Category.objects.all().order_by('level', 'sort_order', 'id')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        parent_id = request.POST.get('parent_id', '')
        sort_order = request.POST.get('sort_order', 0)
        # 确保sort_order是整数类型
        try:
            sort_order = int(sort_order)
        except (ValueError, TypeError):
            sort_order = 0
        
        if not name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': '分类名称不能为空'})
            context = {
                'page_title': '新增分类',
                'user': request.user,
                'all_categories': all_categories,
                'error': '分类名称不能为空',
                'form_data': request.POST,
            }
            return render(request, 'products/category_form.html', context)
        
        if Category.objects.filter(name=name).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': '分类名称已存在'})
            context = {
                'page_title': '新增分类',
                'user': request.user,
                'all_categories': all_categories,
                'error': '分类名称已存在',
                'form_data': request.POST,
            }
            return render(request, 'products/category_form.html', context)
        
        try:
            parent = None
            if parent_id:
                try:
                    parent_id_int = int(parent_id)
                    parent = Category.objects.get(id=parent_id_int)
                except (ValueError, Category.DoesNotExist):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': '无效的父分类ID'})
                    context = {
                        'page_title': '新增分类',
                        'user': request.user,
                        'all_categories': all_categories,
                        'error': '无效的父分类ID',
                        'form_data': request.POST,
                    }
                    return render(request, 'products/category_form.html', context)
            
            # 计算分类级别
            level = 1
            if parent:
                level = parent.level + 1
            
            category = Category.objects.create(
                name=name,
                parent=parent,
                level=level,
                sort_order=sort_order
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'message': '分类创建成功',
                    'category': {
                        'id': category.id,
                        'name': category.name,
                        'level': category.level,
                        'parent_id': category.parent_id
                    }
                })
            
            # 非AJAX请求，重定向到分类列表
            return redirect('products:product_categories')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f'创建失败：{str(e)}'})
            context = {
                'page_title': '新增分类',
                'user': request.user,
                'all_categories': all_categories,
                'error': f'创建失败：{str(e)}',
                'form_data': request.POST,
            }
            return render(request, 'products/category_form.html', context)
    
    # GET请求：显示表单页面
    context = {
        'page_title': '新增分类',
        'user': request.user,
        'all_categories': all_categories,
        'category': None,
    }
    
    return render(request, 'products/category_form.html', context)


@login_required
@manager_required
def admin_category_edit(request, category_id):
    """
    编辑分类页面
    管理员和店长可访问
    """
    category = get_object_or_404(Category, id=category_id)
    
    # 获取所有分类用于父分类选择
    all_categories = Category.objects.all().order_by('level', 'sort_order', 'id')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        parent_id = request.POST.get('parent_id', '')
        sort_order = request.POST.get('sort_order', 0)
        # 确保sort_order是整数类型
        try:
            sort_order = int(sort_order)
        except (ValueError, TypeError):
            sort_order = 0
        
        if not name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': '分类名称不能为空'})
            context = {
                'page_title': '编辑分类',
                'user': request.user,
                'all_categories': all_categories,
                'category': category,
                'error': '分类名称不能为空',
                'form_data': request.POST,
            }
            return render(request, 'products/category_form.html', context)
        
        # 检查名称是否与其他分类重复（排除自己）
        if Category.objects.filter(name=name).exclude(id=category_id).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': '分类名称已存在'})
            context = {
                'page_title': '编辑分类',
                'user': request.user,
                'all_categories': all_categories,
                'category': category,
                'error': '分类名称已存在',
                'form_data': request.POST,
            }
            return render(request, 'products/category_form.html', context)
        
        try:
            parent = None
            if parent_id:
                try:
                    parent_id_int = int(parent_id)
                    parent = Category.objects.get(id=parent_id_int)
                except (ValueError, Category.DoesNotExist):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': '无效的父分类ID'})
                    context = {
                        'page_title': '新增分类',
                        'user': request.user,
                        'all_categories': all_categories,
                        'error': '无效的父分类ID',
                        'form_data': request.POST,
                    }
                    return render(request, 'products/category_form.html', context)
                # 检查是否选择自己或自己的子分类作为父分类
                if parent_id == str(category_id) or (parent_id and int(parent_id) in get_all_child_categories(category)):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': '不能选择自己或子分类作为父分类'})
                    context = {
                        'page_title': '编辑分类',
                        'user': request.user,
                        'all_categories': all_categories,
                        'category': category,
                        'error': '不能选择自己或子分类作为父分类',
                        'form_data': request.POST,
                    }
                    return render(request, 'products/category_form.html', context)
            
            # 计算新的分类级别
            level = 1
            if parent:
                level = parent.level + 1
            
            category.name = name
            category.parent = parent
            category.level = level
            category.sort_order = sort_order
            category.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'message': '分类更新成功',
                    'category': {
                        'id': category.id,
                        'name': category.name,
                        'level': category.level,
                        'parent_id': category.parent_id
                    }
                })
            
            # 非AJAX请求，重定向到分类列表
            return redirect('products:product_categories')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f'更新失败：{str(e)}'})
            context = {
                'page_title': '编辑分类',
                'user': request.user,
                'all_categories': all_categories,
                'category': category,
                'error': f'更新失败：{str(e)}',
                'form_data': request.POST,
            }
            return render(request, 'products/category_form.html', context)
    
    # GET请求：显示表单页面
    context = {
        'page_title': '编辑分类',
        'user': request.user,
        'all_categories': all_categories,
        'category': category,
    }
    
    return render(request, 'products/category_form.html', context)


@login_required
@manager_required
def admin_category_delete(request, category_id):
    """
    删除分类
    管理员和店长可访问
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方式错误'})
    
    category = get_object_or_404(Category, id=category_id)
    
    # 检查是否有子分类
    if Category.objects.filter(parent=category).exists():
        return JsonResponse({'success': False, 'message': '该分类下有子分类，无法删除'})
    
    # 检查是否有关联商品
    if Product.objects.filter(category=category).exists():
        return JsonResponse({'success': False, 'message': '该分类下有关联商品，无法删除'})
    
    try:
        category.delete()
        return JsonResponse({'success': True, 'message': '分类删除成功'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败：{str(e)}'})


@login_required
@manager_required
def admin_category_children(request, category_id):
    """
    获取子分类列表
    管理员和店长可访问
    """
    category = get_object_or_404(Category, id=category_id)
    
    # 获取所有子分类ID（包括间接子分类）
    child_ids = get_all_child_categories(category)
    
    # 包含当前分类
    all_ids = [category_id] + child_ids
    
    # 查询所有相关分类
    categories = Category.objects.filter(id__in=all_ids).order_by('level', 'sort_order', 'id')
    
    data = []
    for cat in categories:
        data.append({
            'id': cat.id,
            'name': cat.name,
            'level': cat.level,
            'parent_id': cat.parent_id,
            'sort_order': cat.sort_order
        })
    
    return JsonResponse({
        'success': True,
        'categories': data,
        'total': len(data)
    })


@login_required
@manager_required
def admin_stock(request):
    """
    库存管理页面
    管理员和店长可访问
    """
    context = {
        'page_title': '库存管理',
        'user': request.user,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'public/empty_page_content.html', context)
    
    return render(request, 'public/empty_page.html', context)


@login_required
@manager_required
def admin_stock_logs(request):
    """
    库存日志页面
    管理员和店长可访问
    """
    from django.utils import timezone
    from datetime import datetime
    
    # 获取筛选参数
    operator_search = request.GET.get('operator', '')
    product_search = request.GET.get('product', '')
    order_id = request.GET.get('order_id', '')
    change_type_filter = request.GET.get('change_type', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    page = request.GET.get('page', 1)
    
    # 基础查询
    logs = StockLog.objects.select_related('product', 'operator', 'order').order_by('-create_time')
    
    # 按操作人搜索
    if operator_search:
        logs = logs.filter(operator__username__icontains=operator_search)
    
    # 按商品搜索（名称或ID）
    if product_search:
        if product_search.isdigit():
            logs = logs.filter(product_id=int(product_search))
        else:
            logs = logs.filter(product__name__icontains=product_search)
    
    # 按订单ID搜索
    if order_id:
        if order_id.isdigit():
            logs = logs.filter(order_id=int(order_id))
    
    # 按变动类型筛选（增加/减少）
    if change_type_filter == 'increase':
        logs = logs.filter(change_type__in=['purchase', 'return'])
    elif change_type_filter == 'decrease':
        logs = logs.filter(change_type__in=['sale', 'adjust'])
    
    # 按时间范围筛选
    if start_date:
        try:
            from datetime import datetime
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            logs = logs.filter(create_time__gte=start_datetime)
        except ValueError:
            pass
    
    if end_date:
        try:
            from datetime import datetime
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            logs = logs.filter(create_time__lte=end_datetime)
        except ValueError:
            pass
    
    # 分页
    paginator = Paginator(logs, 20)
    try:
        logs = paginator.page(page)
    except PageNotAnInteger:
        logs = paginator.page(1)
    except EmptyPage:
        logs = paginator.page(paginator.num_pages)
    
    context = {
        'page_title': '库存日志',
        'user': request.user,
        'logs': logs,
        'operator_search': operator_search,
        'product_search': product_search,
        'order_id': order_id,
        'change_type_filter': change_type_filter,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    # 判断是否为AJAX请求
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'products/stock_logs_content.html', context)
    
    return render(request, 'products/stock_logs.html', context)


@login_required
def api_search_products(request):
    """
    收银台商品搜索API
    支持按条码或名称搜索商品
    返回JSON格式数据
    """
    keyword = request.GET.get('keyword', '').strip()
    search_type = request.GET.get('type', 'barcode')  # barcode 或 name
    
    if not keyword:
        return JsonResponse({'success': False, 'message': '请输入搜索关键词'})
    
    # 基础查询 - 只查询上架的商品
    products = Product.objects.filter(status=True)
    
    if search_type == 'barcode':
        # 按条码精确搜索
        products = products.filter(barcode=keyword)
    else:
        # 按名称模糊搜索，同时支持完整条码搜索
        products = products.filter(
            Q(name__icontains=keyword) | Q(barcode=keyword)
        )
    
    # 限制返回数量
    products = products[:20]
    
    # 构建返回数据
    data = []
    for product in products:
        data.append({
            'id': product.id,
            'barcode': product.barcode,
            'name': product.name,
            'price': float(product.price),
            'unit': product.unit,
            'category': product.category.name if product.category else '未分类',
            'stock': product.stock,
            'image': product.image.url if product.image else None
        })
    
    return JsonResponse({
        'success': True,
        'data': data,
        'count': len(data)
    })


@login_required
@manager_required
def batch_import_products(request):
    """
    批量导入商品
    管理员和店长可访问
    """
    if request.method != 'POST':
        return JsonResponse({'code': '0', 'message': '请求方式错误'})
    
    if 'excel_file' not in request.FILES:
        return JsonResponse({'code': '0', 'message': '请选择Excel文件'})
    
    excel_file = request.FILES['excel_file']
    
    # 检查文件类型
    if not excel_file.name.endswith(('.xlsx', '.xls')):
        return JsonResponse({'code': '0', 'message': '只支持 .xlsx 和 .xls 格式的文件'})
    
    try:
        # 加载Excel文件
        workbook = openpyxl.load_workbook(excel_file)
        worksheet = workbook.active
        
        # 统计信息
        success_count = 0
        failed_count = 0
        
        # 读取数据（跳过表头）
        rows = list(worksheet.iter_rows(min_row=2, max_row=101, values_only=True))
        
        if len(rows) > 100:
            return JsonResponse({'code': '0', 'message': '一次最多处理100条数据'})
        
        # 连续空行计数器
        empty_row_count = 0
        max_empty_rows = 3  # 连续3条空数据判定为导入完毕
        
        for row in rows:
            # 字段顺序：条形码 商品名称 所属分类ID 零售价 成本价 当前库存 库存预警阈值 单位
            barcode = row[0] if row[0] else None
            name = row[1]
            category_id = row[2]
            price = row[3]
            cost = row[4]
            stock = row[5] if row[5] else 0
            warning_stock = row[6] if row[6] else 5
            unit = row[7] if row[7] else '件'
            
            # 检查是否为空行（所有关键字段都为空）
            is_empty_row = not name and not category_id and price is None and cost is None
            
            if is_empty_row:
                empty_row_count += 1
                # 连续3条空数据判定为导入完毕
                if empty_row_count >= max_empty_rows:
                    break
                continue
            else:
                # 重置空行计数器
                empty_row_count = 0
            
            # 检查必填字段
            if not name or not category_id or price is None or cost is None:
                failed_count += 1
                continue
            
            # 检查分类是否存在
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                failed_count += 1
                continue
            
            # 检查条形码是否重复
            if barcode and Product.objects.filter(barcode=barcode).exists():
                failed_count += 1
                continue
            
            try:
                # 创建商品
                product = Product.objects.create(
                    barcode=barcode,
                    name=name,
                    category=category,
                    price=price,
                    cost=cost,
                    stock=stock,
                    warning_stock=warning_stock,
                    unit=unit,
                    status=True  # 默认为上架状态
                )
                success_count += 1
            except Exception as e:
                failed_count += 1
                continue
        
        return JsonResponse({
            'code': '1',
            'message': f'导入完成，成功 {success_count} 条，失败 {failed_count} 条',
            'data': {
                'success_count': success_count,
                'failed_count': failed_count
            }
        })
        
    except Exception as e:
        return JsonResponse({'code': '0', 'message': f'导入失败：{str(e)}'})
