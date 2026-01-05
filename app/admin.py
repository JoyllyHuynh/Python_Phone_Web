from django.contrib import admin
from .models import *
from .models import Payment_VNPay

# 1. Đăng ký các model cơ bản (Không cần tùy chỉnh giao diện)
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)


# 2. Đăng ký Brand với BrandAdmin
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'image')
    prepopulated_fields = {'slug': ('name',)} 
    search_fields = ('name',)

admin.site.register(Brand, BrandAdmin)

class CustomerTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(CustomerType, CustomerTypeAdmin)

class PromotionAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_value', 'is_percentage', 'promotion_type', 'active', 'start_date', 'end_date')
    search_fields = ('code', 'event_name')
    list_filter = ('active', 'promotion_type', 'start_date')

    filter_horizontal = ('target_products', 'target_brands', 'target_users', 'target_customer_types')

    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('code', 'description', 'promotion_type', 'discount_value', 'is_percentage', 'active', 'event_name')
        }),
        ('Thời gian áp dụng', {
            'fields': ('start_date', 'end_date')
        }),
        ('Phạm vi Sản phẩm (Để trống = Toàn sàn)', {
            'fields': ('target_brands', 'target_products'),
            'description': 'Chọn Hãng hoặc Sản phẩm cụ thể. Nếu chọn cả hai, hệ thống sẽ kiểm tra cả hai.'
        }),
        ('Đối tượng Khách hàng (Để trống = Tất cả)', {
            'fields': ('target_customer_types', 'target_users'),
            'description': 'Chọn hạng thành viên hoặc người dùng cụ thể.'
        }),
    )

admin.site.register(Promotion, PromotionAdmin)

# 4. Đăng ký Order với OrderAdmin
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'date_ordered', 'complete', 'transaction_id', 'get_cart_total', 'get_final_total')
    readonly_fields = ('get_cart_total', 'get_final_total')

admin.site.register(Order, OrderAdmin)

# 5. Đăng ký Review với ReviewAdmin (CHỈ ĐĂNG KÝ 1 LẦN Ở ĐÂY)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'content', 'sentiment_label', 'rating')

    def sentiment_label(self, obj):
        if obj.sentiment == 1:
            return "Tích cực"
        elif obj.sentiment == 0:
            return "Tiêu cực"
        return "Chưa phân tích"

    sentiment_label.short_description = "Cảm xúc"

admin.site.register(Review, ReviewAdmin)
admin.site.register(Payment_VNPay)