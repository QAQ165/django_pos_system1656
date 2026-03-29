from django.db import models

class Member(models.Model):
    """
    会员信息表
    """
    card_no = models.CharField(max_length=30, unique=True, verbose_name='会员卡号')
    name = models.CharField(max_length=100, verbose_name='会员姓名')
    phone = models.CharField(max_length=11, unique=True, null=True, blank=True, verbose_name='手机号')
    points = models.IntegerField(default=0, verbose_name='积分')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='储值余额')
    level = models.CharField(max_length=20, default='普通', verbose_name='会员等级')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='注册时间')
    last_visit_time = models.DateTimeField(null=True, blank=True, verbose_name='最后消费时间')

    class Meta:
        db_table = 'member'
        verbose_name = '会员'
        verbose_name_plural = '会员'
        indexes = [
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f'{self.card_no} {self.name}'