from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    用户表，继承 Django 的 AbstractUser，添加角色字段。
    """
    ROLE_CHOICES = (
        ('admin', '管理员'),
        ('manager', '店长'),
        ('cashier', '收银员'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier', verbose_name='角色')
    phone = models.CharField(max_length=11, blank=True, default='', verbose_name='手机号')

    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = '用户'
        indexes = [
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'