from decimal import Decimal
from django.conf import settings
from .models import Product


class Cart:
    """
    Lớp quản lý Giỏ hàng thông qua Session.
    """

    def __init__(self, request):
        """
        Khởi tạo giỏ hàng.
        """
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            # Lưu một giỏ hàng rỗng trong session nếu chưa có
            cart = self.session['cart'] = {}
        self.cart = cart

    def __iter__(self):
        """
        Lặp qua các mục trong giỏ hàng và lấy Product objects từ database.
        """
        product_ids = self.cart.keys()
        # Lấy các đối tượng Product và tạo ánh xạ ID -> Product
        products = Product.objects.filter(id__in=product_ids)

        cart = self.cart.copy()

        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            item['price'] = float(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """
        Đếm tổng số lượng sản phẩm (items) trong giỏ hàng.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def add(self, product, quantity=1, update_quantity=False):
        """
        Thêm sản phẩm vào giỏ hoặc cập nhật số lượng.
        """
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}

        if update_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity

        self.save()

    def save(self):
        # Đánh dấu session là đã thay đổi để đảm bảo nó được lưu
        self.session.modified = True

    def remove(self, product):
        """
        Xóa sản phẩm khỏi giỏ hàng.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def get_total_price(self, selected_ids=None):
        """
        Tính tổng tiền.
        - Nếu selected_ids = None: Tính tổng toàn bộ giỏ hàng.
        - Nếu có selected_ids (list các chuỗi ID): Chỉ tính tổng các sản phẩm trong list đó.
        """
        total = 0
        for p_id, item in self.cart.items():
            # Nếu có danh sách chọn lọc, và ID sản phẩm này không nằm trong đó -> Bỏ qua
            if selected_ids and p_id not in selected_ids:
                continue

            total += float(item['price']) * item['quantity']

        return total

    def clear(self):
        """
        Xóa toàn bộ giỏ hàng khỏi session.
        """
        del self.session['cart']
        self.save()