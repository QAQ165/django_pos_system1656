from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from users.decorators import admin_required
from .models import SystemConfig, BackupLog
import json
import os
import datetime
from django.core import serializers
from users.models import User
from members.models import Member
from products.models import Category, Product,StockLog
from sales.models import Order, OrderItem

from sales.models import SuspendedCart
from pos_system.settings import BASE_DIR


@login_required
@admin_required
def admin_settings(request):
    """
    系统设置页面
    仅管理员可访问
    """
    # 处理POST请求（AJAX）
    if request.method == 'POST':
        return handle_settings_post(request)
    
    # 获取系统配置
    config = SystemConfig.get_config()
    
    # 获取备份日志（最近10条）
    backup_logs = BackupLog.objects.all().order_by('-created_at')[:10]
    
    context = {
        'page_title': '系统设置',
        'user': request.user,
        'config': config,
        'backup_logs': backup_logs,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'system/settings_content.html', context)
    
    return render(request, 'system/settings.html', context)


def handle_settings_post(request):
    """
    处理系统设置的POST请求
    """
    try:
        action = request.POST.get('action')
        
        if action == 'save_config':
            return save_config(request)
        elif action == 'manual_backup':
            return manual_backup(request)
        elif action == 'restore_data':
            backup_filepath = request.POST.get('backup_filepath')
            return restore_data(request, backup_filepath)
        else:
            return JsonResponse({
                'success': False,
                'message': '未知的操作类型'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'操作失败：{str(e)}'
        })


def save_config(request):
    """
    保存系统配置
    """
    try:
        config = SystemConfig.get_config()
        
        # 更新配置
        config.system_name = request.POST.get('system_name', '零售店POS系统')
        config.backup_type = request.POST.get('backup_type', 'manual')
        config.backup_period = request.POST.get('backup_period', 'daily')
        config.enable_captcha = request.POST.get('enable_captcha') == 'on'
        
        # 积分赠送设置
        threshold_amount = request.POST.get('threshold_amount')
        reward_points = request.POST.get('reward_points')
        
        if threshold_amount is not None:
            try:
                config.threshold_amount = float(threshold_amount)
            except:
                config.threshold_amount = 0
        
        if reward_points is not None:
            try:
                config.reward_points = int(reward_points)
            except:
                config.reward_points = 0
        
        config.updated_by = request.user
        config.save()
        
        return JsonResponse({
            'success': True,
            'message': '设置保存成功！'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'保存失败：{str(e)}'
        })


def get_backup_files(request):
    """
    从backups文件夹获取所有备份文件列表
    """
    try:
        backup_dir = os.path.join(BASE_DIR, 'backups')
        
        if not os.path.exists(backup_dir):
            return JsonResponse({
                'code': '1',
                'message': 'success',
                'data': []
            })
        
        backup_files = []
        
        for filename in os.listdir(backup_dir):
            if filename.startswith('backup_') and filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                
                file_stat = os.stat(filepath)
                file_size = file_stat.st_size
                file_mtime = datetime.datetime.fromtimestamp(file_stat.st_mtime)
                
                backup_files.append({
                    'filename': filename,
                    'filepath': filepath,
                    'file_size': file_size,
                    'created_at': file_mtime.strftime('%Y-%m-%d %H:%M:%S'),
                    'backup_type': '手动备份'
                })
        
        backup_files.sort(key=lambda x: x['created_at'], reverse=True)
        
        return JsonResponse({
            'code': '1',
            'message': 'success',
            'data': backup_files
        })
    except Exception as e:
        return JsonResponse({
            'code': '0',
            'message': f'获取备份文件列表失败：{str(e)}',
            'data': []
        })


def manual_backup(request):
    """
    执行手动备份
    限制：一天只能备份一次
    """
    try:
        # 备份文件夹路径
        backup_dir = os.path.join(BASE_DIR, 'backups')
        
        # 检查文件夹是否存在
        if not os.path.exists(backup_dir):
            return JsonResponse({
                'success': False,
                'message': '备份文件夹不存在，请先创建 backups 文件夹'
            })
        
        # 检查今天是否已经有备份记录
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + datetime.timedelta(days=1)
        
        today_backup_exists = BackupLog.objects.filter(
            backup_type='manual',
            status='success',
            created_at__gte=today_start,
            created_at__lt=today_end
        ).exists()
        
        if today_backup_exists:
            return JsonResponse({
                'success': False,
                'message': '今天已经备份过了，一天只能备份一次'
            })
        
        # 计算今天的备份次数
        today = datetime.datetime.now().strftime('%Y%m%d')
        backup_count = 1
        
        # 查找今天的备份文件
        for filename in os.listdir(backup_dir):
            if filename.startswith(f'backup_{today}_') and filename.endswith('.json'):
                try:
                    count = int(filename.split('_')[-1].split('.')[0])
                    if count >= backup_count:
                        backup_count = count + 1
                except:
                    pass
        
        # 生成备份文件名
        backup_filename = f'backup_{today}_{backup_count}.json'
        backup_filepath = os.path.join(backup_dir, backup_filename)
        
        # 收集所有表的数据
        backup_data = {
            'backup_time': datetime.datetime.now().isoformat(),
            'tables': {}
        }
        
        # 备份用户表
        users = User.objects.all()
        backup_data['tables']['user'] = json.loads(serializers.serialize('json', users))
        
        # 备份系统配置表
        system_configs = SystemConfig.objects.all()
        backup_data['tables']['system_config'] = json.loads(serializers.serialize('json', system_configs))
        
        # 备份会员表
        members = Member.objects.all()
        backup_data['tables']['member'] = json.loads(serializers.serialize('json', members))
        
        # 备份分类表
        categories = Category.objects.all()
        backup_data['tables']['category'] = json.loads(serializers.serialize('json', categories))
        
        # 备份商品表
        products = Product.objects.all()
        backup_data['tables']['product'] = json.loads(serializers.serialize('json', products))
        
        # 备份订单表
        orders = Order.objects.all()
        backup_data['tables']['order'] = json.loads(serializers.serialize('json', orders))
        
        # 备份订单项表
        order_items = OrderItem.objects.all()
        backup_data['tables']['orderitem'] = json.loads(serializers.serialize('json', order_items))
        
        # 备份库存日志表
        stock_logs = StockLog.objects.all()
        backup_data['tables']['stocklog'] = json.loads(serializers.serialize('json', stock_logs))
        
        # 备份备份日志表
        backup_logs = BackupLog.objects.all()
        backup_data['tables']['backup_log'] = json.loads(serializers.serialize('json', backup_logs))
        
        # 备份挂起购物车表
        # suspended_carts = SuspendedCart.objects.all()
        # backup_data['tables']['suspendedcart'] = json.loads(serializers.serialize('json', suspended_carts))
        
        # 写入JSON文件
        with open(backup_filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        # 获取文件大小
        file_size = os.path.getsize(backup_filepath)
        
        # 记录备份日志
        backup_log = BackupLog.objects.create(
            backup_type='manual',
            file_name=backup_filename,
            file_path=backup_filepath,
            file_size=file_size,
            operator=request.user,
            status='success'
        )
        
        return JsonResponse({
            'success': True,
            'message': '备份成功！'
        })
    except Exception as e:
        # 记录失败日志
        BackupLog.objects.create(
            backup_type='manual',
            file_name='',
            file_path='',
            file_size=0,
            operator=request.user,
            status='failed',
            error_message=str(e)
        )
        
        return JsonResponse({
            'success': False,
            'message': f'备份失败：{str(e)}'
        })


def restore_data(request, backup_filepath):
    """
    执行数据恢复
    按照正确流程：1. 删除数据库 2. 创建新数据库 3. 自动生成系统表 4. 恢复业务数据
    """
    import logging
    import subprocess
    import sys
    from django.conf import settings
    from django.db import transaction, connection
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"开始恢复数据，备份文件: {backup_filepath}")
        
        # 1. 首先执行一次备份
        logger.info("恢复前执行备份操作")
        backup_response = manual_backup(request)
        if not backup_response.json().get('success'):
            logger.warning("恢复前的备份失败，但继续执行恢复操作")
        
        # 2. 检查备份文件是否存在
        if not os.path.exists(backup_filepath):
            logger.error("备份文件不存在")
            return JsonResponse({
                'success': False,
                'message': '备份文件不存在，无法恢复'
            })
        
        # 4. 读取备份数据并验证格式
        try:
            with open(backup_filepath, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # 验证必要的字段
            if 'tables' not in backup_data:
                logger.error("备份文件格式错误：缺少tables字段")
                return JsonResponse({
                    'success': False,
                    'message': '备份文件格式错误：缺少tables字段'
                })
        except json.JSONDecodeError as e:
            logger.error(f"备份文件解析失败：{str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'备份文件解析失败：{str(e)}'
            })
        
        # 5. 执行数据库重置和恢复流程
        db_config = settings.DATABASES['default']
        db_name = db_config['NAME']
        engine = db_config['ENGINE']
        
        logger.info(f"数据库引擎: {engine}")
        
        # 构建数据库连接命令
        if engine == 'django.db.backends.sqlite3':
            # SQLite数据库处理
            if os.path.exists(db_name):
                logger.info(f"删除SQLite数据库文件: {db_name}")
                os.remove(db_name)
            # 创建新的空数据库文件
            logger.info(f"创建新的SQLite数据库文件: {db_name}")
            open(db_name, 'a').close()
        else:
            # 对于非SQLite数据库，使用更彻底的方法：重新创建数据库
            try:
                # 获取数据库连接信息
                db_user = db_config.get('USER', '')
                db_password = db_config.get('PASSWORD', '')
                db_host = db_config.get('HOST', 'localhost')
                db_port = db_config.get('PORT', '')
                
                if engine == 'django.db.backends.mysql':
                    # MySQL处理：删除并重新创建数据库
                    logger.info("处理MySQL数据库：删除并重新创建")
                    
                    # 先连接到MySQL服务器（不指定数据库）
                    import MySQLdb
                    conn = MySQLdb.connect(
                        host=db_host,
                        user=db_user,
                        password=db_password,
                        port=int(db_port) if db_port else 3306
                    )
                    conn.autocommit(True)
                    cursor = conn.cursor()
                    
                    # 删除并重新创建数据库
                    cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
                    cursor.execute(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    
                    cursor.close()
                    conn.close()
                    
                    logger.info(f"MySQL数据库 {db_name} 已重新创建")
                elif engine == 'django.db.backends.postgresql':
                    # PostgreSQL处理：删除并重新创建数据库
                    logger.info("处理PostgreSQL数据库：删除并重新创建")
                    
                    # 使用psycopg2连接到PostgreSQL服务器
                    import psycopg2
                    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
                    
                    conn = psycopg2.connect(
                        host=db_host,
                        user=db_user,
                        password=db_password,
                        port=int(db_port) if db_port else 5432,
                        dbname='postgres'  # 连接到默认数据库
                    )
                    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                    cursor = conn.cursor()
                    
                    # 终止所有连接到目标数据库的会话
                    cursor.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}'")
                    
                    # 删除并重新创建数据库
                    cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
                    cursor.execute(f"CREATE DATABASE {db_name} ENCODING 'UTF8'")
                    
                    cursor.close()
                    conn.close()
                    
                    logger.info(f"PostgreSQL数据库 {db_name} 已重新创建")
                else:
                    # 其他数据库类型：使用删除表的方式
                    logger.info(f"处理{engine}数据库：删除所有表")
                    with connection.cursor() as cursor:
                        if engine == 'django.db.backends.mysql':
                            cursor.execute("SHOW TABLES")
                            tables = cursor.fetchall()
                            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                        elif engine == 'django.db.backends.postgresql':
                            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                            tables = cursor.fetchall()
                            cursor.execute("SET CONSTRAINTS ALL DEFERRED")
                        
                        # 删除所有表
                        for table in tables:
                            table_name = table[0]
                            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}` CASCADE")
                        
                        if engine == 'django.db.backends.mysql':
                            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                    
                    logger.info("所有表已删除")
            except ImportError as e:
                logger.error(f"缺少数据库驱动：{str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'缺少数据库驱动：{str(e)}。请安装相应的数据库驱动。'
                })
            except Exception as e:
                logger.error(f"数据库操作失败：{str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'数据库操作失败：{str(e)}'
                })
        
        # 6. 运行migrate命令生成系统表
        try:
            logger.info("执行migrate命令生成系统表")
            python_exe = sys.executable
            migrate_cmd = [python_exe, 'manage.py', 'migrate']
            migrate_result = subprocess.run(
                migrate_cmd, 
                capture_output=True, 
                text=True, 
                cwd=BASE_DIR,
                timeout=60  # 添加超时设置
            )
            
            if migrate_result.returncode != 0:
                logger.error(f"执行migrate失败：{migrate_result.stderr}")
                return JsonResponse({
                    'success': False,
                    'message': f'执行migrate失败：{migrate_result.stderr}'
                })
            logger.info("migrate命令执行成功")
        except subprocess.TimeoutExpired:
            logger.error("执行migrate超时")
            return JsonResponse({
                'success': False,
                'message': '执行migrate超时'
            })
        except Exception as e:
            logger.error(f"执行migrate时发生错误：{str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'执行migrate时发生错误：{str(e)}'
            })
        
        # 7. 恢复业务数据
        logger.info("开始恢复业务数据")
        
        # 使用事务确保数据一致性
        try:
            with transaction.atomic():
                # 按顺序恢复数据，确保外键关系正确
                # 1. 先恢复用户表
                if 'user' in backup_data['tables']:
                    logger.info("恢复用户表数据")
                    for item in backup_data['tables']['user']:
                        # 提取用户字段，排除多对多字段
                        user_fields = item['fields'].copy()
                        # 处理多对多字段
                        groups = user_fields.pop('groups', [])
                        user_permissions = user_fields.pop('user_permissions', [])
                        
                        # 处理时间字段，将ISO格式转换为数据库可接受的格式
                        import datetime
                        for field_name, field_value in user_fields.items():
                            if field_value and isinstance(field_value, str):
                                # 尝试解析ISO格式的时间字符串
                                if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                                    try:
                                        # 解析ISO格式
                                        if field_value.endswith('Z'):
                                            # 处理带Z的格式
                                            dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                                        else:
                                            # 处理带时区的格式
                                            dt = datetime.datetime.fromisoformat(field_value)
                                        # 转换为数据库可接受的格式
                                        user_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception as e:
                                        logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        from django.db import connection
                        with connection.cursor() as cursor:
                            # 构建插入语句
                            fields = list(user_fields.keys()) + ['id']
                            values = list(user_fields.values()) + [item['pk']]
                            
                            # 处理字段名和值
                            field_names = ', '.join(fields)
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            # 执行插入
                            cursor.execute(
                                f"INSERT INTO user ({field_names}) VALUES ({placeholders})",
                                values
                            )
                        
                        # 处理多对多关系
                        if groups:
                            user = User.objects.get(id=item['pk'])
                            user.groups.set(groups)
                        if user_permissions:
                            if not 'user' in locals():
                                user = User.objects.get(id=item['pk'])
                            user.user_permissions.set(user_permissions)
                
                # 2. 恢复系统配置表
                if 'system_config' in backup_data['tables']:
                    logger.info("恢复系统配置表数据")
                    for item in backup_data['tables']['system_config']:
                        # 处理外键字段
                        config_fields = item['fields'].copy()
                        updated_by_id = config_fields.pop('updated_by', None)
                        
                        # 处理时间字段，将ISO格式转换为数据库可接受的格式
                        import datetime
                        for field_name, field_value in config_fields.items():
                            if field_value and isinstance(field_value, str):
                                # 尝试解析ISO格式的时间字符串
                                if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                                    try:
                                        # 解析ISO格式
                                        if field_value.endswith('Z'):
                                            # 处理带Z的格式
                                            dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                                        else:
                                            # 处理带时区的格式
                                            dt = datetime.datetime.fromisoformat(field_value)
                                        # 转换为数据库可接受的格式
                                        config_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception as e:
                                        logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        from django.db import connection
                        with connection.cursor() as cursor:
                            # 构建插入语句
                            fields = list(config_fields.keys()) + ['id', 'updated_by_id'] if updated_by_id else list(config_fields.keys()) + ['id']
                            values = list(config_fields.values()) + [item['pk'], updated_by_id] if updated_by_id else list(config_fields.values()) + [item['pk']]
                            
                            # 处理字段名和值
                            field_names = ', '.join(fields)
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            # 执行插入
                            cursor.execute(
                                f"INSERT INTO system_config ({field_names}) VALUES ({placeholders})",
                                values
                            )
            
                # 3. 恢复会员表
                if 'member' in backup_data['tables']:
                    logger.info("恢复会员表数据")
                    for item in backup_data['tables']['member']:
                        # 处理时间字段，将ISO格式转换为数据库可接受的格式
                        member_fields = item['fields'].copy()
                        import datetime
                        for field_name, field_value in member_fields.items():
                            if field_value and isinstance(field_value, str):
                                # 尝试解析ISO格式的时间字符串
                                if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                                    try:
                                        # 解析ISO格式
                                        if field_value.endswith('Z'):
                                            # 处理带Z的格式
                                            dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                                        else:
                                            # 处理带时区的格式
                                            dt = datetime.datetime.fromisoformat(field_value)
                                        # 转换为数据库可接受的格式
                                        member_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception as e:
                                        logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        from django.db import connection
                        with connection.cursor() as cursor:
                            # 构建插入语句
                            fields = list(member_fields.keys()) + ['id']
                            values = list(member_fields.values()) + [item['pk']]
                            
                            # 处理字段名和值
                            field_names = ', '.join(fields)
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            # 执行插入
                            cursor.execute(
                                f"INSERT INTO member ({field_names}) VALUES ({placeholders})",
                                values
                            )
            
                # 4. 恢复分类表
                if 'category' in backup_data['tables']:
                    logger.info("恢复分类表数据")
                    for item in backup_data['tables']['category']:
                        # 处理外键字段
                        category_fields = item['fields'].copy()
                        parent_id = category_fields.pop('parent', None)
                        
                        # 处理时间字段，将ISO格式转换为数据库可接受的格式
                        import datetime
                        for field_name, field_value in category_fields.items():
                            if field_value and isinstance(field_value, str):
                                # 尝试解析ISO格式的时间字符串
                                if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                                    try:
                                        # 解析ISO格式
                                        if field_value.endswith('Z'):
                                            # 处理带Z的格式
                                            dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                                        else:
                                            # 处理带时区的格式
                                            dt = datetime.datetime.fromisoformat(field_value)
                                        # 转换为数据库可接受的格式
                                        category_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception as e:
                                        logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        from django.db import connection
                        with connection.cursor() as cursor:
                            # 构建插入语句
                            fields = list(category_fields.keys()) + ['id', 'parent_id'] if parent_id else list(category_fields.keys()) + ['id']
                            values = list(category_fields.values()) + [item['pk'], parent_id] if parent_id else list(category_fields.values()) + [item['pk']]
                            
                            # 处理字段名和值
                            field_names = ', '.join(fields)
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            # 执行插入
                            cursor.execute(
                                f"INSERT INTO category ({field_names}) VALUES ({placeholders})",
                                values
                            )
            
                # 5. 恢复商品表
                if 'product' in backup_data['tables']:
                    logger.info("恢复商品表数据")
                    for item in backup_data['tables']['product']:
                        # 处理外键字段
                        product_fields = item['fields'].copy()
                        category_id = product_fields.pop('category', None)
                        
                        # 处理时间字段，将ISO格式转换为数据库可接受的格式
                        import datetime
                        for field_name, field_value in product_fields.items():
                            if field_value and isinstance(field_value, str):
                                # 尝试解析ISO格式的时间字符串
                                if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                                    try:
                                        # 解析ISO格式
                                        if field_value.endswith('Z'):
                                            # 处理带Z的格式
                                            dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                                        else:
                                            # 处理带时区的格式
                                            dt = datetime.datetime.fromisoformat(field_value)
                                        # 转换为数据库可接受的格式
                                        product_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception as e:
                                        logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        from django.db import connection
                        with connection.cursor() as cursor:
                            # 构建插入语句
                            fields = list(product_fields.keys()) + ['id', 'category_id'] if category_id else list(product_fields.keys()) + ['id']
                            values = list(product_fields.values()) + [item['pk'], category_id] if category_id else list(product_fields.values()) + [item['pk']]
                            
                            # 处理字段名和值
                            field_names = ', '.join(fields)
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            # 执行插入
                            cursor.execute(
                                f"INSERT INTO product ({field_names}) VALUES ({placeholders})",
                                values
                            )
            
                # 6. 恢复订单表
                if 'order' in backup_data['tables']:
                    logger.info("恢复订单表数据")
                    for item in backup_data['tables']['order']:
                        # 处理外键字段
                        order_fields = item['fields'].copy()
                        cashier_id = order_fields.pop('cashier', None)
                        member_id = order_fields.pop('member', None)
                        
                        # 处理时间字段，将ISO格式转换为数据库可接受的格式
                        import datetime
                        for field_name, field_value in order_fields.items():
                            if field_value and isinstance(field_value, str):
                                # 尝试解析ISO格式的时间字符串
                                if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                                    try:
                                        # 解析ISO格式
                                        if field_value.endswith('Z'):
                                            # 处理带Z的格式
                                            dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                                        else:
                                            # 处理带时区的格式
                                            dt = datetime.datetime.fromisoformat(field_value)
                                        # 转换为数据库可接受的格式
                                        order_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception as e:
                                        logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        from django.db import connection
                        with connection.cursor() as cursor:
                            # 构建插入语句
                            fields = list(order_fields.keys()) + ['id', 'cashier_id', 'member_id']
                            values = list(order_fields.values()) + [item['pk'], cashier_id, member_id]
                            
                            # 处理字段名和值
                            field_names = ', '.join(fields)
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            # 执行插入
                            cursor.execute(
                                f"INSERT INTO `order` ({field_names}) VALUES ({placeholders})",
                                values
                            )
            
                # 7. 恢复订单项表
                if 'orderitem' in backup_data['tables']:
                    logger.info("恢复订单项表数据")
                    for item in backup_data['tables']['orderitem']:
                        # 处理外键字段
                        order_item_fields = item['fields'].copy()
                        order_id = order_item_fields.pop('order', None)
                        product_id = order_item_fields.pop('product', None)
                        
                        # 处理时间字段，将ISO格式转换为数据库可接受的格式
                        import datetime
                        for field_name, field_value in order_item_fields.items():
                            if field_value and isinstance(field_value, str):
                                # 尝试解析ISO格式的时间字符串
                                if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                                    try:
                                        # 解析ISO格式
                                        if field_value.endswith('Z'):
                                            # 处理带Z的格式
                                            dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                                        else:
                                            # 处理带时区的格式
                                            dt = datetime.datetime.fromisoformat(field_value)
                                        # 转换为数据库可接受的格式
                                        order_item_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception as e:
                                        logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        from django.db import connection
                        with connection.cursor() as cursor:
                            # 构建插入语句
                            fields = list(order_item_fields.keys()) + ['id', 'order_id', 'product_id']
                            values = list(order_item_fields.values()) + [item['pk'], order_id, product_id]
                            
                            # 处理字段名和值
                            field_names = ', '.join(fields)
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            # 执行插入
                            cursor.execute(
                                f"INSERT INTO orderitem ({field_names}) VALUES ({placeholders})",
                                values
                            )
            
                # 8. 恢复库存日志表
                if 'stocklog' in backup_data['tables']:
                    logger.info("恢复库存日志表数据")
                    for item in backup_data['tables']['stocklog']:
                        # 处理外键字段
                        stock_log_fields = item['fields'].copy()
                        product_id = stock_log_fields.pop('product', None)
                        order_id = stock_log_fields.pop('order', None)
                        operator_id = stock_log_fields.pop('operator', None)
                        
                        # 处理时间字段，将ISO格式转换为数据库可接受的格式
                        import datetime
                        for field_name, field_value in stock_log_fields.items():
                            if field_value and isinstance(field_value, str):
                                # 尝试解析ISO格式的时间字符串
                                if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                                    try:
                                        # 解析ISO格式
                                        if field_value.endswith('Z'):
                                            # 处理带Z的格式
                                            dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                                        else:
                                            # 处理带时区的格式
                                            dt = datetime.datetime.fromisoformat(field_value)
                                        # 转换为数据库可接受的格式
                                        stock_log_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception as e:
                                        logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        from django.db import connection
                        with connection.cursor() as cursor:
                            # 构建插入语句
                            fields = list(stock_log_fields.keys()) + ['id', 'product_id', 'order_id', 'operator_id']
                            values = list(stock_log_fields.values()) + [item['pk'], product_id, order_id, operator_id]
                            
                            # 处理字段名和值
                            field_names = ', '.join(fields)
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            # 执行插入
                            cursor.execute(
                                f"INSERT INTO stocklog ({field_names}) VALUES ({placeholders})",
                                values
                            )
            
                # 9. 恢复备份日志表
                if 'backup_log' in backup_data['tables']:
                    logger.info("恢复备份日志表数据")
                    for item in backup_data['tables']['backup_log']:
                        # 处理外键字段
                        log_fields = item['fields'].copy()
                        operator_id = log_fields.pop('operator', None)
                        
                        # 处理时间字段，将ISO格式转换为数据库可接受的格式
                        import datetime
                        for field_name, field_value in log_fields.items():
                            if field_value and isinstance(field_value, str):
                                # 尝试解析ISO格式的时间字符串
                                if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                                    try:
                                        # 解析ISO格式
                                        if field_value.endswith('Z'):
                                            # 处理带Z的格式
                                            dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                                        else:
                                            # 处理带时区的格式
                                            dt = datetime.datetime.fromisoformat(field_value)
                                        # 转换为数据库可接受的格式
                                        log_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except Exception as e:
                                        logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        from django.db import connection
                        with connection.cursor() as cursor:
                            # 构建插入语句
                            fields = list(log_fields.keys()) + ['id', 'operator_id'] if operator_id else list(log_fields.keys()) + ['id']
                            values = list(log_fields.values()) + [item['pk'], operator_id] if operator_id else list(log_fields.values()) + [item['pk']]
                            
                            # 处理字段名和值
                            field_names = ', '.join(fields)
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            # 执行插入
                            cursor.execute(
                                f"INSERT INTO backup_log ({field_names}) VALUES ({placeholders})",
                                values
                            )
            
                # 10. 恢复挂起购物车表
                # if 'suspendedcart' in backup_data['tables']:
                #     logger.info("恢复挂起购物车表数据")
                #     for item in backup_data['tables']['suspendedcart']:
                #         # 处理外键字段
                #         cart_fields = item['fields'].copy()
                #         cashier_id = cart_fields.pop('cashier', None)
                        
                #         # 处理时间字段，将ISO格式转换为数据库可接受的格式
                #         import datetime
                #         for field_name, field_value in cart_fields.items():
                #             if field_value and isinstance(field_value, str):
                #                 # 尝试解析ISO格式的时间字符串
                #                 if 'T' in field_value and ('Z' in field_value or '+' in field_value):
                #                     try:
                #                         # 解析ISO格式
                #                         if field_value.endswith('Z'):
                #                             # 处理带Z的格式
                #                             dt = datetime.datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                #                         else:
                #                             # 处理带时区的格式
                #                             dt = datetime.datetime.fromisoformat(field_value)
                #                         # 转换为数据库可接受的格式
                #                         cart_fields[field_name] = dt.strftime('%Y-%m-%d %H:%M:%S')
                #                     except Exception as e:
                #                         logger.warning(f"解析时间字段 {field_name} 失败: {e}")
                        
                        # 直接使用SQL插入，绕过Django的auto_now/auto_now_add机制
                        # from django.db import connection
                        # with connection.cursor() as cursor:
                        #     # 构建插入语句
                        #     fields = list(cart_fields.keys()) + ['id', 'cashier_id'] if cashier_id else list(cart_fields.keys()) + ['id']
                        #     values = list(cart_fields.values()) + [item['pk'], cashier_id] if cashier_id else list(cart_fields.values()) + [item['pk']]
                            
                        #     # 处理字段名和值
                        #     field_names = ', '.join(fields)
                        #     placeholders = ', '.join(['%s'] * len(values))
                            
                        #     # 执行插入
                        #     cursor.execute(
                        #         f"INSERT INTO suspendedcart ({field_names}) VALUES ({placeholders})",
                        #         values
                        #     )
            
            logger.info("数据恢复成功")
            return JsonResponse({
                'success': True,
                'message': '数据恢复成功！系统将在2秒后跳转到登录页面。',
                'redirect': '/login/'
            })
        except Exception as e:
            logger.error(f"数据恢复过程中出错：{str(e)}")
            # 事务会自动回滚
            return JsonResponse({
                'success': False,
                'message': f'恢复失败：{str(e)}'
            })
    except Exception as e:
        logger.error(f"恢复操作失败：{str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'恢复失败：{str(e)}'
        })
