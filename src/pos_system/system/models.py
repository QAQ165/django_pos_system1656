from django.db import models


class SystemConfig(models.Model):
    """
    系统配置表
    存储系统的各项配置参数
    """
    # 数据备份策略
    BACKUP_TYPE_CHOICES = (
        ('manual', '手动备份'),
        ('auto', '定期备份'),
    )
    
    BACKUP_PERIOD_CHOICES = (
        ('daily', '每天'),
        ('weekly', '每周'),
        ('monthly', '每月'),
    )
    
    # 备份策略：手动/定期
    backup_type = models.CharField(
        max_length=20, 
        choices=BACKUP_TYPE_CHOICES, 
        default='manual',
        verbose_name='备份策略'
    )
    
    # 定期备份周期：每天/每周/每月
    backup_period = models.CharField(
        max_length=20, 
        choices=BACKUP_PERIOD_CHOICES, 
        default='daily',
        verbose_name='备份周期'
    )
    
    # 是否启用登录验证码
    enable_captcha = models.BooleanField(
        default=True, 
        verbose_name='启用登录验证码'
    )
    
    # 系统名称
    system_name = models.CharField(
        max_length=100, 
        default='零售店POS系统',
        verbose_name='系统名称'
    )
    
    # 积分赠送设置 - 满额金额
    threshold_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name='满额金额(元)'
    )
    
    # 积分赠送设置 - 赠送积分
    reward_points = models.IntegerField(
        default=0, 
        verbose_name='赠送积分'
    )
    
    # 最后修改时间
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='最后修改时间'
    )
    
    # 修改人
    updated_by = models.ForeignKey(
        'users.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_constraint=False,
        verbose_name='修改人'
    )

    class Meta:
        db_table = 'system_config'
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'

    def __str__(self):
        return f'系统配置 - {self.system_name}'

    @classmethod
    def get_config(cls):
        """
        获取系统配置
        如果不存在则创建默认配置
        """
        config, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'backup_type': 'manual',
                'backup_period': 'daily',
                'enable_captcha': True,
                'system_name': '零售店POS系统',
                'threshold_amount': 0,
                'reward_points': 0
            }
        )
        return config


class BackupLog(models.Model):
    """
    备份日志表
    记录每次备份的信息
    """
    BACKUP_TYPE_CHOICES = (
        ('manual', '手动备份'),
        ('auto', '自动备份'),
    )
    
    STATUS_CHOICES = (
        ('success', '成功'),
        ('failed', '失败'),
    )
    
    # 备份类型
    backup_type = models.CharField(
        max_length=20, 
        choices=BACKUP_TYPE_CHOICES,
        verbose_name='备份类型'
    )
    
    # 备份文件名
    file_name = models.CharField(
        max_length=255, 
        verbose_name='备份文件名'
    )
    
    # 备份文件路径
    file_path = models.CharField(
        max_length=500, 
        verbose_name='备份文件路径'
    )
    
    # 文件大小（字节）
    file_size = models.BigIntegerField(
        default=0, 
        verbose_name='文件大小'
    )
    
    # 备份状态
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        verbose_name='备份状态'
    )
    
    # 错误信息（如果失败）
    error_message = models.TextField(
        blank=True, 
        verbose_name='错误信息'
    )
    
    # 操作人
    operator = models.ForeignKey(
        'users.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_constraint=False,
        verbose_name='操作人'
    )
    
    # 创建时间
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='备份时间'
    )

    class Meta:
        db_table = 'backup_log'
        verbose_name = '备份日志'
        verbose_name_plural = '备份日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_backup_type_display()} - {self.created_at.strftime("%Y-%m-%d %H:%M")}'


# 保留原有的SystemSettings模型，用于其他灵活配置
class SystemSettings(models.Model):
    """
    系统设置表（key-value形式）
    用于存储其他灵活的配置项
    """
    key = models.CharField(max_length=100, unique=True, verbose_name='配置键')
    value = models.TextField(verbose_name='配置值')
    description = models.CharField(max_length=255, blank=True, verbose_name='描述')

    class Meta:
        db_table = 'systemsettings'
        verbose_name = '系统设置（扩展）'
        verbose_name_plural = '系统设置（扩展）'

    def __str__(self):
        return self.key
