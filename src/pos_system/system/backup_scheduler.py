import os
import json
import datetime
import threading
import time
from django.core import serializers
from .models import SystemConfig, BackupLog
from users.models import User
from members.models import Member
from products.models import Category, Product, StockLog
from sales.models import Order, OrderItem
from pos_system.settings import BASE_DIR

class BackupScheduler:
    """
    定时备份调度器
    根据系统配置中的备份策略和周期执行备份
    """
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """
        启动定时备份调度器
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._scheduler_loop)
            self.thread.daemon = True
            self.thread.start()
            print("定时备份调度器已启动")
    
    def stop(self):
        """
        停止定时备份调度器
        """
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=5)
            print("定时备份调度器已停止")
    
    def _scheduler_loop(self):
        """
        调度器主循环
        """
        while self.running:
            try:
                # 获取系统配置
                config = SystemConfig.get_config()
                
                # 检查是否启用了定期备份
                if config.backup_type == 'auto':
                    # 检查是否需要执行备份
                    if self._should_backup(config.backup_period):
                        print(f"执行定时备份，周期: {config.backup_period}")
                        self._perform_backup()
                
                # 每小时检查一次
                for _ in range(60):
                    if not self.running:
                        break
                    time.sleep(60)

            except Exception as e:
                print(f"定时备份调度器错误: {str(e)}")
                # 出错后等待一段时间再继续
                time.sleep(300)
    
    def _should_backup(self, period):
        """
        检查是否应该执行备份
        """
        now = datetime.datetime.now()
        
        # 检查今天是否已经有成功的自动备份
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + datetime.timedelta(days=1)
        
        today_backup_exists = BackupLog.objects.filter(
            backup_type='auto',
            status='success',
            created_at__gte=today_start,
            created_at__lt=today_end
        ).exists()
        
        if today_backup_exists:
            return False
        
        # 根据周期检查是否应该备份
        if period == 'daily':
            # 每天备份，检查当前时间是否在指定备份时间
            # 默认为每天凌晨1点
            return now.hour == 1 and now.minute < 10
        elif period == 'weekly':
            # 每周备份，检查是否是周一凌晨1点
            return now.weekday() == 0 and now.hour == 1 and now.minute < 10
        elif period == 'monthly':
            # 每月备份，检查是否是1号凌晨1点
            return now.day == 1 and now.hour == 1 and now.minute < 10
        
        return False
    
    def _perform_backup(self):
        """
        执行备份操作
        与手动备份功能相同
        """
        try:
            # 备份文件夹路径
            backup_dir = os.path.join(BASE_DIR, 'backups')
            
            # 检查文件夹是否存在
            if not os.path.exists(backup_dir):
                print("备份文件夹不存在，创建 backups 文件夹")
                os.makedirs(backup_dir, exist_ok=True)
            
            # 计算今天的备份次数
            today = datetime.datetime.now().strftime('%Y%m%d')
            backup_count = 1
            
            # 查找今天的备份文件
            if os.path.exists(backup_dir):
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
            
            # 写入JSON文件
            with open(backup_filepath, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            # 获取文件大小
            file_size = os.path.getsize(backup_filepath)
            
            # 记录备份日志（使用系统用户或None）
            # 尝试获取系统管理员用户
            system_user = None
            try:
                system_user = User.objects.filter(role='admin').first()
            except:
                pass
            
            backup_log = BackupLog.objects.create(
                backup_type='auto',
                file_name=backup_filename,
                file_path=backup_filepath,
                file_size=file_size,
                operator=system_user,
                status='success'
            )
            
            print(f"定时备份成功：{backup_filename}")
            
        except Exception as e:
            # 记录失败日志
            try:
                system_user = None
                try:
                    system_user = User.objects.filter(role='admin').first()
                except:
                    pass
                
                BackupLog.objects.create(
                    backup_type='auto',
                    file_name='',
                    file_path='',
                    file_size=0,
                    operator=system_user,
                    status='failed',
                    error_message=str(e)
                )
            except:
                pass
            
            print(f"定时备份失败：{str(e)}")

# 创建全局备份调度器实例
backup_scheduler = BackupScheduler()
