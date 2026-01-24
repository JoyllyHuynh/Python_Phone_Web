from django.db import models
from django.contrib.auth.models import User, Group
from django import forms
from datetime import timedelta

from django.utils import timezone


class CustomerType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Tên hạng")
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=False)
    name = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=200, null=True)
    phone = models.CharField(max_length=15, null=True)
    customer_type = models.ForeignKey(CustomerType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Hạng thành viên")

    def __str__(self):
        return self.name if self.name else "Unknown Customer"

class Brand(models.Model):
    name = models.CharField(max_length=200, null=True, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    image = models.ImageField(upload_to='brands/', null=True, blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, null=True, verbose_name="Tên sản phẩm")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Giá bán (Mặc định)")
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Giá gốc (Mặc định)")

    digital = models.BooleanField(default=False, null=True, blank=False)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', null=True, verbose_name="Hãng sản xuất")

    screen_size = models.CharField(max_length=50, null=True, blank=True, verbose_name="Màn hình")
    ram = models.CharField(max_length=50, null=True, blank=True, verbose_name="RAM")
    chip = models.CharField(max_length=100, null=True, blank=True, verbose_name="Chip xử lý")
    rear_camera = models.CharField(max_length=255, null=True, blank=True, verbose_name="Camera sau")
    front_camera = models.CharField(max_length=255, null=True, blank=True, verbose_name="Camera trước")
    battery = models.CharField(max_length=255, null=True, blank=True, verbose_name="Pin & Sạc")

    sold_count = models.IntegerField(default=0, verbose_name="Đã bán")
    average_rating = models.FloatField(default=0.0, verbose_name="Đánh giá TB")

    def __str__(self):
        return self.name

    @property
    def get_image_url(self):
        try:
            url = self.image.url
        except:
            if self.image_url:
                url = self.image_url
            else:
                url = ''
        return url

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    storage_size = models.CharField(max_length=50, verbose_name="Dung lượng") # Vd: 128GB, 256GB, 1TB
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Giá bán riêng")
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Giá gốc riêng")

    stock = models.IntegerField(default=0, verbose_name="Số lượng tồn")

    class Meta:
        verbose_name = "Biến thể sản phẩm"
        verbose_name_plural = "Các biến thể (Dung lượng/Màu...)"

    def __str__(self):
        return f"{self.product.name} - {self.storage_size}"

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False, null=True, blank=False)
    transaction_id = models.CharField(max_length=100, null=True)

    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    discount_amount = models.FloatField(default=0, blank=True, null=True)
    estimated_delivery_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return str(self.id)

    @property
    def get_cart_items(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.quantity for item in orderitems])
        return total

    @property
    def get_cart_total(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.get_total for item in orderitems])
        return total

    @property
    def get_final_total(self):
        # Lấy tổng tiền hàng
        total = self.get_cart_total
        if self.discount_amount:
            total -= self.discount_amount
        return max(total, 0)

    def save(self, *args, **kwargs):
        if not self.estimated_delivery_date:
            current_date = self.date_ordered if self.date_ordered else timezone.now()
            self.estimated_delivery_date = current_date.date() + timedelta(days=7)
        super().save(*args, **kwargs)
    
class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    @property

    def get_total(self):
        if self.product:
            return float(self.product.price) * self.quantity
        return 0

class ShippingAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    address = models.CharField(max_length=200, null=True)
    city = models.CharField(max_length=200, null=True)
    state = models.CharField(max_length=200, null=True)
    phone_number = models.CharField(max_length=10, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.address

class Promotion(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_value = models.FloatField()
    is_percentage = models.BooleanField(default=False)

    event_name = models.CharField(max_length=100, default="Sự kiện")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(default=0, verbose_name="Giới hạn số lượng (0 là không giới hạn)")
    used_count = models.IntegerField(default=0, verbose_name="Đã sử dụng")

    target_products = models.ManyToManyField('Product', blank=True, related_name='product_promotions', verbose_name="Sản phẩm cụ thể")
    target_brands = models.ManyToManyField('Brand', blank=True, related_name='brand_promotions', verbose_name="Toàn bộ hãng")

    target_users = models.ManyToManyField(User, blank=True, related_name='private_promotions', verbose_name="Người dùng cụ thể")
    target_customer_types = models.ManyToManyField(CustomerType, blank=True, related_name='type_promotions', verbose_name="Hạng thành viên áp dụng")

    PROMOTION_TYPES = [
        ('normal', 'Thông thường'),
        ('new_arrival', 'Sản phẩm mới'),
        ('vip', 'Khách hàng thân thiết'),
        ('flash_sale', 'Flash Sale'),
        ('new_customer', 'Khách hàng mới'),
        ('holiday', 'Dịp lễ hội'),

    ]
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPES, default='normal')

    def __str__(self):
        return self.code


    def is_valid_for_product(self, product):

        has_product_limit = self.target_products.exists()
        has_brand_limit = self.target_brands.exists()

        if not has_product_limit and not has_brand_limit:
            return True

        check_product = product in self.target_products.all() if has_product_limit else False
        check_brand = product.brand in self.target_brands.all() if has_brand_limit else False

        return check_product or check_brand

    def is_valid_for_user(self, user):
        if not user.is_authenticated:
            return False

        if self.target_users.exists() and user not in self.target_users.all():
            return False
        if self.usage_limit > 0 and self.used_count >= self.usage_limit:
            return False
        try:
            customer = user.customer
        except Customer.DoesNotExist:
            return False

        completed_orders = Order.objects.filter(customer=customer, complete=True)
        total_spent = sum([order.get_final_total for order in completed_orders])

        if self.promotion_type == 'new_customer':
            if total_spent > 0:
                return False

        elif self.promotion_type == 'vip':
            if total_spent < 5000:
                return False

        if self.target_customer_types.exists():
            if customer.customer_type not in self.target_customer_types.all():
                return False

        return True

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    rating = models.IntegerField(default=5, null=True, blank=True)

    # 1 = positive, 0 = negative, None = neutral / unknown
    sentiment = models.IntegerField(null=True, blank=True)

    date_added = models.DateTimeField(auto_now_add=True)

    ai_result = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-date_added']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

    @property
    def get_sentiment_display(self):
        if self.sentiment == 1:
            return "Tích cực"
        elif self.sentiment == 0:
            return "Tiêu cực"
        return "Trung lập"

    

class Payment_VNPay(models.Model):
    order_id = models.CharField(max_length=200, null=True, blank=True)
    amount = models.FloatField(default=0.0, null=True, blank=True)
    order_desc = models.CharField(max_length=200, null=True, blank=True)
    vnp_TransactionNo = models.CharField(max_length=100, null=True, blank=True)
    vnp_ResponseCode = models.CharField(max_length=100, null=True, blank=True)
    


class PaymentForm(forms.Form):
    order_id = forms.CharField(max_length=250)
    order_type = forms.CharField(max_length=20)
    amount = forms.IntegerField()
    order_desc = forms.CharField(max_length=100)
    bank_code = forms.CharField(max_length=20, required=False)
    language = forms.CharField(max_length=2)


# app/models.py

class Store(models.Model):
    name = models.CharField(max_length=200, verbose_name="Tên cửa hàng")
    address = models.CharField(max_length=500, verbose_name="Địa chỉ")
    phone = models.CharField(max_length=20, verbose_name="Số điện thoại")

    # Để hiển thị trên map, cần toạ độ. Bạn có thể lấy trên google map (click phải vào địa điểm chọn 'What's here')
    latitude = models.FloatField(verbose_name="Vĩ độ (Latitude)")
    longitude = models.FloatField(verbose_name="Kinh độ (Longitude)")

    # Khu vực để lọc (nếu muốn)
    region = models.CharField(max_length=50, choices=[
        ('MB', 'Miền Bắc'),
        ('MT', 'Miền Trung'),
        ('MN', 'Miền Nam')
    ], default='MN', verbose_name="Khu vực")

    def __str__(self):
        return self.name