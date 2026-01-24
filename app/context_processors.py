# app/context_processors.py

from .models import Order
from django.conf import settings

def cart_context(request):
    """
    Cung cấp tổng số lượng sản phẩm trong giỏ hàng cho tất cả các template.
    """
    cart_total_quantity = 0
    
    # CHỈ TÍNH TOÁN KHI NGƯỜI DÙNG ĐÃ ĐĂNG NHẬP
    if request.user.is_authenticated:
        try:
            # 1. Lấy đối tượng Customer
            # Nếu user đã đăng nhập, phải có đối tượng Customer liên quan
            customer = request.user.customer
            
            # 2. Lấy Order chưa hoàn thành
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            
            # 3. Lấy tổng số lượng (sử dụng @property get_cart_items)
            cart_total_quantity = order.get_cart_items
            
        except Exception as e:
            # Bắt lỗi nếu request.user.customer chưa được tạo hoặc Order/OrderItem lỗi
            print(f"Lỗi Context Processor: {e}") 
            cart_total_quantity = 0
    
    return {
        # Sử dụng tên biến thống nhất: cartItems (vì nó là tên hay được dùng nhất)
        'cartItems': cart_total_quantity 
    }

# app/context_processors.py
from .models import Brand

def brands_in_navbar(request):
    # Lấy tất cả các hãng, sắp xếp theo tên
    all_brands = Brand.objects.all().order_by('name')
    return {'navbar_brands': all_brands}

def turnstile_keys(request):
    return {"TURNSTILE_SITE_KEY": getattr(settings, "TURNSTILE_SITE_KEY", "")}