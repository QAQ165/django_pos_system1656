from django.db import models
from users.models import User
from members.models import Member
from products.models import Product

class Order(models.Model):
    """
    销售订单主表
    """
    PAYMENT_CHOICES = (
        ('cash', '现金'),
        ('wechat', '微信'),
        ('alipay', '支付宝'),
        ('member', '会员卡'),
    )
    STATUS_CHOICES = (
        ('paid', '已支付'),
        ('refunded', '已退款'),
        ('canceled', '已取消'),
        ('suspend', '挂起'),
    )
    order_no = models.CharField(max_length=30, unique=True, verbose_name='订单号')
    cashier = models.ForeignKey(User, on_delete=models.RESTRICT, db_constraint=False, verbose_name='收银员')
    member = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, verbose_name='会员')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='订单总额')
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='实收金额')
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='找零')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, verbose_name='支付方式')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid', verbose_name='订单状态')
    remark = models.TextField(blank=True, verbose_name='备注')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='下单时间')

    class Meta:
        db_table = 'order'
        verbose_name = '订单'
        verbose_name_plural = '订单'
        indexes = [
            models.Index(fields=['order_no']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return self.order_no


class OrderItem(models.Model):
    """
    订单商品明细表
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', db_constraint=False, verbose_name='所属订单')
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, db_constraint=False, verbose_name='商品')
    quantity = models.IntegerField(verbose_name='数量')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成交单价')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='小计')

    class Meta:
        db_table = 'orderitem'
        verbose_name = '订单明细'
        verbose_name_plural = '订单明细'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f'{self.order.order_no} - {self.product.name}'


class SuspendedCart(models.Model):
    """
    挂单购物车临时表
    """
    STATUS_CHOICES = (
        (1, '挂单中'),
        (2, '已取单'),
    )
    cashier = models.ForeignKey(User, on_delete=models.CASCADE, db_constraint=False, verbose_name='收银员')
    cart_data = models.JSONField(verbose_name='购物车内容')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='挂单时间')
    note = models.CharField(max_length=255, blank=True, verbose_name='备注')
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name='状态')

    class Meta:
        db_table = 'suspendedcart'
        verbose_name = '挂单'
        verbose_name_plural = '挂单'
        indexes = [
            models.Index(fields=['cashier']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'挂单 {self.id} - {self.cashier.username} - {self.get_status_display()}'