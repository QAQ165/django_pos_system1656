from django.db import models
from users.models import User  # 用于 StockLog 中的 operator 外键

class Category(models.Model):
    """
    商品分类表（支持多级）
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='分类名称')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, db_constraint=False, verbose_name='父分类')
    level = models.IntegerField(default=1, verbose_name='分类级别')
    sort_order = models.IntegerField(default=0, verbose_name='排序序号')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'category'
        verbose_name = '商品分类'
        verbose_name_plural = '商品分类'
        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['level']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.parent:
            self.level = self.parent.level + 1
        else:
            self.level = 1
        
        # 确保sort_order是整数类型
        try:
            self.sort_order = int(self.sort_order)
        except (ValueError, TypeError):
            self.sort_order = 0
        
        if self.sort_order > 100:
            self.sort_order = 100
        
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    商品主表
    """
    barcode = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='条形码')
    name = models.CharField(max_length=200, verbose_name='商品名称')
    category = models.ForeignKey(Category, on_delete=models.RESTRICT, db_constraint=False, verbose_name='所属分类')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='零售价')
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='成本价')
    stock = models.IntegerField(default=0, verbose_name='当前库存')
    warning_stock = models.IntegerField(default=5, verbose_name='预警库存')
    unit = models.CharField(max_length=20, default='件', verbose_name='单位')
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name='商品图片')
    status = models.BooleanField(default=True, verbose_name='上架状态')
    expiry_date = models.DateTimeField(null=True, blank=True, verbose_name='过期时间')
    shelf_life = models.IntegerField(null=True, blank=True, verbose_name='保质期(天)')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='最后修改时间')

    class Meta:
        db_table = 'product'
        verbose_name = '商品'
        verbose_name_plural = '商品'
        indexes = [
            models.Index(fields=['barcode']),
            models.Index(fields=['name']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.name


class StockLog(models.Model):
    """
    库存变动日志表
    """
    CHANGE_TYPE_CHOICES = (
        ('sale', '销售出库'),
        ('purchase', '采购入库'),
        ('return', '退货入库'),
        ('adjust', '盘点调整'),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_constraint=False, verbose_name='商品')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES, verbose_name='变动类型')
    quantity = models.IntegerField(verbose_name='变动数量')
    before_stock = models.IntegerField(verbose_name='变动前库存')
    after_stock = models.IntegerField(verbose_name='变动后库存')
    order = models.ForeignKey('sales.Order', null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, verbose_name='关联订单')
    operator = models.ForeignKey(User, on_delete=models.RESTRICT, db_constraint=False, verbose_name='操作人')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='变动时间')

    class Meta:
        db_table = 'stocklog'
        verbose_name = '库存日志'
        verbose_name_plural = '库存日志'
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['order']),
            models.Index(fields=['operator']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return f'{self.product.name} {self.get_change_type_display()} {self.quantity}'