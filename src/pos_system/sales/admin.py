from django.contrib import admin
from .models import Order, OrderItem, SuspendedCart

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'subtotal')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_no', 'cashier', 'member', 'total_amount', 'paid_amount', 'change_amount', 'payment_method', 'status', 'create_time')
    list_filter = ('payment_method', 'status', 'create_time')
    search_fields = ('order_no', 'cashier__username', 'member__name')
    readonly_fields = ('order_no', 'create_time')
    inlines = [OrderItemInline]
    fieldsets = (
        ('订单信息', {
            'fields': ('order_no', 'cashier', 'member', 'remark')
        }),
        ('金额信息', {
            'fields': ('total_amount', 'paid_amount', 'change_amount', 'payment_method')
        }),
        ('状态', {
            'fields': ('status',)
        }),
        ('时间信息', {
            'fields': ('create_time',),
            'classes': ('collapse',)
        }),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price', 'subtotal')
    list_filter = ('order__create_time',)
    search_fields = ('order__order_no', 'product__name')
    readonly_fields = ('subtotal',)

@admin.register(SuspendedCart)
class SuspendedCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'cashier', 'create_time', 'note')
    list_filter = ('create_time',)
    search_fields = ('cashier__username', 'note')
    readonly_fields = ('cart_data', 'create_time')