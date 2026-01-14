from django.contrib import admin
from .models import *
from .models import Payment_VNPay
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin

admin.site.register(Customer)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)


class ProductResource(resources.ModelResource):
    brand = fields.Field(
        column_name='brand',
        attribute='brand',
        widget=ForeignKeyWidget(Brand, field='name')
    )

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'price', 'old_price', 'digital', 'brand', 'image_url',
            'screen_size', 'storage', 'ram', 'chip',
            'rear_camera', 'front_camera', 'battery',
            'sold_count', 'average_rating'
        )
        export_order = fields
        import_id_fields = ('id',)

class ProductVariantResource(resources.ModelResource):
    product = fields.Field(
        column_name='product',
        attribute='product',
        widget=ForeignKeyWidget(Product, field='name')
    )

    class Meta:
        model = ProductVariant
        fields = ('id', 'product', 'storage_size', 'price', 'old_price', 'stock')
        import_id_fields = ('id',)

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('storage_size', 'price', 'old_price', 'stock')

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    inlines = [ProductVariantInline]

    # 1. Xóa 'storage' khỏi list_display
    list_display = ('name', 'price_display', 'brand', 'sold_count', 'variant_count', 'view_image_status')

    # 2. Xóa 'storage' khỏi list_filter (vì Product không còn field này để lọc)
    list_filter = ('brand', 'ram')

    search_fields = ('name', 'brand__name', 'chip')

    fieldsets = (
        ('Thông tin chung', {
            'fields': ('name', 'brand', 'price', 'old_price', 'digital', 'sold_count', 'average_rating')
        }),
        ('Hình ảnh', {
            'fields': ('image', 'image_url')
        }),
        ('Cấu hình chi tiết', {
            # 3. Xóa 'storage' khỏi fieldsets nhập liệu
            'fields': ('screen_size', 'chip', 'ram', 'rear_camera', 'front_camera', 'battery')
        }),
    )

    def view_image_status(self, obj):
        if obj.image: return "Local Upload"
        elif obj.image_url: return "URL Link"
        return "No Image"
    view_image_status.short_description = "Nguồn ảnh"

    def price_display(self, obj):
        return f"{obj.price:,.0f} đ"
    price_display.short_description = "Giá bán"

    def variant_count(self, obj):
        return obj.variants.count()
    variant_count.short_description = "Số biến thể"

@admin.register(ProductVariant)
class ProductVariantAdmin(ImportExportModelAdmin):
    resource_class = ProductVariantResource
    list_display = ('product', 'storage_size', 'price', 'stock')
    search_fields = ('product__name',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

class CustomerTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(CustomerType, CustomerTypeAdmin)

class PromotionAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_value', 'is_percentage', 'promotion_type','usage_limit', 'used_count', 'active', 'start_date', 'end_date')
    search_fields = ('code', 'event_name')
    list_filter = ('active', 'promotion_type', 'start_date')

    filter_horizontal = ('target_products', 'target_brands', 'target_users', 'target_customer_types')

    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('code', 'description', 'promotion_type', 'discount_value', 'is_percentage','usage_limit', 'used_count', 'active', 'event_name')
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

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'date_ordered', 'complete', 'transaction_id','coupon_code', 'get_cart_total', 'get_final_total')
    readonly_fields = ('get_cart_total', 'get_final_total')

admin.site.register(Order, OrderAdmin)

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