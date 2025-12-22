from django.contrib import admin
from .models import *

admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)

class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'image')
    prepopulated_fields = {'slug': ('name',)} 
    search_fields = ('name',)

admin.site.register(Brand, BrandAdmin)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_value', 'is_percentage', 'start_date', 'end_date', 'active')
    search_fields = ('code', 'event_name')
    list_filter = ('active', 'is_percentage')

admin.site.register(Promotion, PromotionAdmin)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'date_ordered', 'complete', 'transaction_id', 'get_cart_total', 'get_final_total')
    readonly_fields = ('get_cart_total', 'get_final_total')

admin.site.register(Order, OrderAdmin)