from .cart import Cart # Giả sử bạn có class Cart nằm trong app/cart.py hoặc app/models.py

def cart_context(request):
    """
    Thêm tổng số lượng sản phẩm trong giỏ hàng vào mọi template context.
    Giúp hiển thị số lượng sản phẩm trên icon giỏ hàng.
    """
    try:
        # Khởi tạo giỏ hàng từ request
        cart = Cart(request) 
        # Lấy tổng số lượng (total_quantity) của giỏ hàng
        cart_total_quantity = sum(item['quantity'] for item in cart)
    except Exception:
        # Đảm bảo không bị lỗi nếu Cart chưa được cấu hình đúng
        cart_total_quantity = 0

    return {
        # Tên biến này (cart_total_quantity) sẽ được sử dụng trong mọi template
        'cart_total_quantity': cart_total_quantity 
    }