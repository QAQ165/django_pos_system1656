from django.contrib import admin
from .models import Category, Product, StockLog

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'parent', 'sort_order', 'create_time')
    list_filter = ('parent',)
    search_fields = ('name',)
    ordering = ('sort_order',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'barcode', 'name', 'category', 'price', 'cost', 'stock', 'warning_stock', 'status', 'create_time')
    list_filter = ('category', 'status')
    search_fields = ('barcode', 'name')
    list_editable = ('price', 'cost', 'stock', 'warning_stock', 'status')  # 允许在列表页直接编辑
    readonly_fields = ('create_time', 'update_time')
    fieldsets = (
        ('基本信息', {
            'fields': ('barcode', 'name', 'category', 'unit', 'image', 'status')
        }),
        ('价格与库存', {
            'fields': ('price', 'cost', 'stock', 'warning_stock')
        }),
        ('时间信息', {
            'fields': ('create_time', 'update_time'),
            'classes': ('collapse',)  # 折叠显示
        }),
    )

@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'change_type', 'quantity', 'before_stock', 'after_stock', 'operator', 'create_time')
    list_filter = ('change_type', 'create_time')
    search_fields = ('product__name', 'operator__username')
    readonly_fields = ('create_time',)