from django.db import models
from django.contrib.auth.models import User, Group

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
    slug = models.SlugField(max_length=200, unique=True) # Dùng cho URL thân thiện
    image = models.ImageField(upload_to='brands/', null=True, blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    digital = models.BooleanField(default=False, null=True, blank=False)
    image = models.ImageField(null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')

    def __str__(self):
        return self.name
    @property
    def ImageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url
    
class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False, null=True, blank=False)
    transaction_id = models.CharField(max_length=100, null=True)

    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    discount_amount = models.FloatField(default=0, blank=True, null=True)

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
    
class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    @property
    def get_total(self):
        return float(self.product.price) * self.quantity

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

    target_products = models.ManyToManyField('Product', blank=True, related_name='product_promotions', verbose_name="Sản phẩm cụ thể")
    target_brands = models.ManyToManyField('Brand', blank=True, related_name='brand_promotions', verbose_name="Toàn bộ hãng")

    target_users = models.ManyToManyField(User, blank=True, related_name='private_promotions', verbose_name="Người dùng cụ thể")
    target_customer_types = models.ManyToManyField(CustomerType, blank=True, related_name='type_promotions', verbose_name="Hạng thành viên áp dụng")

    PROMOTION_TYPES = [
        ('normal', '🎫 Thông thường'),
        ('new_arrival', '🔥 Sản phẩm mới'),
        ('vip', '💎 Khách hàng thân thiết'),
        ('flash_sale', '⚡ Flash Sale'),
        ('new customer', '🌟 Khách hàng mới'),
        ('holiday', '🎉 Dịp lễ hội'),

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

        has_user_limit = self.target_users.exists()
        has_type_limit = self.target_customer_types.exists()

        if not has_user_limit and not has_type_limit:
            return True

        if has_user_limit and user in self.target_users.all():
            return True

        if has_type_limit:
            try:
                customer = user.customer
                if customer.customer_type in self.target_customer_types.all():
                    return True
            except:
                return False
        return False

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    # Thêm dòng này vào hoặc sửa lại nếu đã có
    rating = models.IntegerField(default=5, null=True, blank=True) 
    sentiment = models.IntegerField(null=True, blank=True) 
    date_added = models.DateTimeField(auto_now_add=True)

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
        return "Chưa xác định"