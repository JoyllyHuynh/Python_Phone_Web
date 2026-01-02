import re
import joblib
import os
from datetime import timedelta
from django.utils import timezone
from .models import Product, Review
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import *
import json
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404, redirect
from .models import Product
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth import logout
from django.db.models import Q
from django.db.models import Sum
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import intcomma
from .models import Customer
from .models import Promotion

MODEL_PATH = os.path.join(settings.BASE_DIR, 'app', 'model_data', 'model_cam_xuc.pkl')
VECTOR_PATH = os.path.join(settings.BASE_DIR, 'app', 'model_data', 'vectorizer.pkl')

def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        data = request.POST
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')

        if len(password) < 8:
            messages.error(request, "Mật khẩu phải có ít nhất 8 ký tự!")
            return redirect('register')

        if not re.search(r'[A-Z]', password):
            messages.error(request, "Mật khẩu phải chứa ít nhất 1 chữ cái in hoa!")
            return redirect('register')

        if not re.search(r'\d', password):
            messages.error(request, "Mật khẩu phải chứa ít nhất 1 chữ số!")
            return redirect('register')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, "Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt (!@#...)!")
            return redirect('register')

        if password != confirm_password:
            messages.error(request, "Mật khẩu nhập lại không khớp!")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Tên đăng nhập này đã có người sử dụng!")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email này đã được đăng ký!")
            return redirect('register')

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            Customer.objects.create(user=user, name=username, email=email)
            auth_login(request, user)
            messages.success(request, "Tạo tài khoản thành công!")
            return redirect('home')

        except Exception as e:
            messages.error(request, f"Đã có lỗi xảy ra: {e}")
            return redirect('register')

    return render(request, 'app/register.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                auth_login(request, user)
                if request.GET.get('next'):
                    return redirect(request.GET.get('next'))
                return redirect('home')
            else:
                messages.error(request, "Sai mật khẩu hoặc tên đăng nhập.")
        else:
            messages.error(request, "Thông tin không hợp lệ.")
    else:
        form = AuthenticationForm()

    context = {'form': form}
    return render(request, 'app/login.html', context)

def logout_views(request):
    logout(request)
    return redirect('login')

def home(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items = []
        order = {'get_cart_total':0, 'get_cart_items':0}
        cartItems = order['get_cart_items']
    products = Product.objects.all()
    context= {'products': products, 'cartItems': cartItems}
    return render(request, 'app/home.html',context)

def cart(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items = []
        order = {'get_cart_total':0, 'get_cart_items':0}
        cartItems = order['get_cart_items']
    context= {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'app/cart.html',context) 

def checkout(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
    else:
        # Xử lý khách vãng lai (nếu chưa có logic cookie thì để trống)
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}

    # 1. Tổng tiền hàng
    subtotal = order.get_cart_total if hasattr(order, 'get_cart_total') else 0

    # 2. Phí vận chuyển (Logic: > 2 triệu Free, ngược lại 30k)
    shipping_fee = 0 if subtotal >= 2000000 else 30000
    if subtotal == 0: shipping_fee = 0 # Giỏ hàng rỗng thì ship = 0

    # 3. Tái kiểm tra Coupon từ Session
    # (Tại sao phải check lại? Vì user có thể đã xóa bớt hàng làm coupon không còn hợp lệ)
    discount_amount = 0
    coupon_code = request.session.get('coupon_code')

    if coupon_code:
        success, msg, real_discount = apply_coupon_logic(request, order, coupon_code)
        if success:
            discount_amount = real_discount
        else:
            # Nếu không còn hợp lệ thì xóa khỏi session
            del request.session['coupon_code']
            del request.session['coupon_discount']
            messages.warning(request, f"Mã {coupon_code} đã bị hủy: {msg}")

    # 4. Tổng thanh toán cuối cùng
    final_total = subtotal + shipping_fee - discount_amount
    if final_total < 0: final_total = 0

    context = {
        'items': items,
        'order': order,
        'shipping_fee': shipping_fee,
        'discount_amount': discount_amount,
        'final_total': final_total,
        'coupon_code': coupon_code
    }
    return render(request, 'app/checkout.html', context)

# --- VIEW APPLY COUPON ---
def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('coupon_code')
        if request.user.is_authenticated:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(customer=customer, complete=False)

            success, msg, discount = apply_coupon_logic(request, order, code)

            if success:
                request.session['coupon_code'] = code
                request.session['coupon_discount'] = discount
                messages.success(request, msg)
            else:
                messages.error(request, msg)
        else:
            messages.warning(request, "Vui lòng đăng nhập.")
    return redirect('checkout')

def remove_coupon(request):
    if 'coupon_code' in request.session: del request.session['coupon_code']
    if 'coupon_discount' in request.session: del request.session['coupon_discount']
    messages.info(request, "Đã xóa mã giảm giá.")
    return redirect('checkout')

def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']   
    action = data['action']
    customer = request.user.customer
    product = Product.objects.get(id = productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False) 
    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)
    if action == 'add':
        orderItem.quantity += 1
    elif action == 'remove':
        orderItem.quantity -= 1
    orderItem.save()
    if orderItem.quantity <= 0:
        orderItem.delete()
    return JsonResponse('added', safe=False)


def home(request):
    # Lấy tất cả các hãng để truyền vào sidebar/menu
    brands = Brand.objects.all()
    products = Product.objects.all() # hoặc QuerySet sản phẩm nổi bật

    context = {'products': products, 'brands': brands}
    return render(request, 'app/home.html', context)

def product_list_by_brand(request, brand_slug):
    # 1. Lấy tất cả các hãng để hiển thị menu bên trên
    brands = Brand.objects.all()

    # 2. Lấy đối tượng Brand hiện tại (hoặc trả về 404 nếu không tìm thấy)
    current_brand = get_object_or_404(Brand, slug=brand_slug)

    # 3. Lọc tất cả sản phẩm thuộc Brand đó
    products = Product.objects.filter(brand=current_brand)

    context = {
        'products': products,
        'brands': brands,
        'current_brand': current_brand # Dùng để hiển thị tiêu đề
    }
    return render(request, 'app/product_list_by_brand.html', context)

def user_info(request):
    if request.user.is_authenticated:
        try:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            cartItems = order.get_cart_items
        except:
             cartItems = 0
    else:
        cartItems = 0

    context = {'cartItems': cartItems}
    return render(request, 'app/user_info.html', context)
def about(request):
    if request.user.is_authenticated:
        try:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            cartItems = order.get_cart_items
        except:
             cartItems = 0
    else:
        cartItems = 0

    context = {'cartItems': cartItems}
    return render(request, 'app/about.html', context)

# app/views.py
def get_cart_data(request):
    if request.user.is_authenticated:
        customer, created = Customer.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.username, 'email': request.user.email}
        )
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
        return {'items': items, 'order': order, 'cartItems': cartItems}
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = order['get_cart_items']
        return {'items': items, 'order': order, 'cartItems': cartItems}

def contact(request):
    # Logic giỏ hàng (giữ nguyên để header không bị lỗi số lượng)
    if request.user.is_authenticated:
        try:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            cartItems = order.get_cart_items
        except:
            cartItems = 0
    else:
        cartItems = 0

    message_success = False

    # Xử lý khi người dùng ấn nút Gửi
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # Lưu vào database
        Contact.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        message_success = True # Cờ báo thành công để hiển thị popup

    context = {'cartItems': cartItems, 'success': message_success}
    return render(request, 'app/contact.html', context)
def product_list_by_brand(request, brand_slug):

    # 1. Lấy tất cả các hãng để hiển thị sidebar/menu
    brands = Brand.objects.all()

    # 2. Lấy đối tượng Brand hiện tại bằng slug
    current_brand = get_object_or_404(Brand, slug=brand_slug)

    # 3. Lọc tất cả sản phẩm thuộc hãng này
    products = Product.objects.filter(brand=current_brand)

    context = {
        'products': products,
        'brands': brands,
        'current_brand': current_brand,
        # 'cartItems' đã được Context Processor xử lý
    }
    return render(request, 'app/product_list_by_brand.html', context)

def promotion_list(request):

    now = timezone.now()

    promotions = Promotion.objects.filter(active=True)

    if request.user.is_authenticated:
        promotions = promotions.filter(
            Q(target_users__isnull=True) | Q(target_users=request.user)
        ).distinct()
    else:
        promotions = promotions.filter(target_users__isnull=True)

    context = {'promotions': promotions}
    return render(request, 'app/promotion_list.html', context)


try:
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTOR_PATH)
except Exception as e:
    print(f"Lỗi AI: {e}")
    model = vectorizer = None

# --- HÀM CHI TIẾT SẢN PHẨM DUY NHẤT ---
# --- XÓA CÁC HÀM product_detail CŨ VÀ DÙNG BẢN NÀY ---
# --- HÀM CHI TIẾT SẢN PHẨM & GỬI BÌNH LUẬN ---
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == "POST" and request.user.is_authenticated:
        # LỚP 1: Kiểm tra Honeypot (Chặn Bot tự động)
        if request.POST.get('honeypot'):
            return JsonResponse({'status': 'error', 'message': 'Phát hiện hành vi spam!'}, status=400)

        content = request.POST.get('content', '').strip()

        # LỚP 2: Kiểm tra nội dung rác
        if len(content) < 5:
            return JsonResponse({'status': 'error', 'message': 'Bình luận quá ngắn (tối thiểu 5 ký tự).'}, status=400)
        
        # Danh sách từ khóa bị cấm (Blacklist)
        blacklist = ['http', 'www', '.com', '.vn', 'zalo', '09', 'kiếm tiền', 'nhận quà', 'click vào']
        if any(word in content.lower() for word in blacklist):
            return JsonResponse({'status': 'error', 'message': 'Bình luận chứa liên kết hoặc từ ngữ quảng cáo bị cấm.'}, status=400)

        # LỚP 3: Kiểm tra tần suất (Rate Limit) & Nội dung trùng lặp
        last_review = Review.objects.filter(user=request.user).order_by('-date_added').first()
        if last_review:
            # Chặn gửi quá nhanh (phải cách nhau ít nhất 30 giây)
            time_diff = timezone.now() - last_review.date_added
            if time_diff < timedelta(seconds=30):
                return JsonResponse({'status': 'error', 'message': 'Bạn đang gửi quá nhanh. Vui lòng đợi một chút.'}, status=400)
            
            # Chặn nội dung giống hệt bình luận vừa gửi
            if content.lower() == last_review.content.lower():
                return JsonResponse({'status': 'error', 'message': 'Bạn đã gửi nội dung này trước đó.'}, status=400)

        # --- NẾU VƯỢT QUA KIỂM TRA -> TIẾN HÀNH LƯU ---
        sentiment_value = None
        if model and vectorizer:
            try:
                vec = vectorizer.transform([content.lower()])
                sentiment_value = int(model.predict(vec)[0])
            except Exception as e:
                print(f"Lỗi dự đoán AI: {e}")

        review = Review.objects.create(
            product=product,
            user=request.user,
            content=content,
            sentiment=sentiment_value
        )
        
        return JsonResponse({
            'status': 'success',
            'user': request.user.username,
            'content': content,
            'ai_sentiment': review.get_sentiment_display,
            'date': review.date_added.strftime("%d/%m/%Y %H:%M")
        })

    # Phần xử lý GET hiển thị trang (giữ nguyên)
    product_reviews = product.reviews.all() 
    cartItems = 0
    if request.user.is_authenticated:
        try:
            customer = request.user.customer
            order, _ = Order.objects.get_or_create(customer=customer, complete=False)
            cartItems = order.get_cart_items
        except: pass

    context = {'product': product, 'product_reviews': product_reviews, 'cartItems': cartItems}
    return render(request, 'app/product_detail.html', context)


# --- HÀM SỬA BÌNH LUẬN (CŨNG CẦN CHẶN RÁC) ---
def edit_review(request, id):
    if request.method == "POST" and request.user.is_authenticated:
        review = get_object_or_404(Review, id=id, user=request.user)
        new_content = request.POST.get('content', '').strip()
        
        # Kiểm tra nội dung rác khi sửa
        if len(new_content) < 5:
            return JsonResponse({'status': 'error', 'message': 'Nội dung quá ngắn.'}, status=400)
            
        blacklist = ['http', 'www', 'zalo', 'kiếm tiền']
        if any(word in new_content.lower() for word in blacklist):
            return JsonResponse({'status': 'error', 'message': 'Nội dung sửa đổi chứa từ cấm.'}, status=400)

        if new_content:
            review.content = new_content
            if model and vectorizer:
                try:
                    vec = vectorizer.transform([new_content.lower()])
                    review.sentiment = int(model.predict(vec)[0])
                except: pass
            review.save()
            
            return JsonResponse({
                'status': 'success',
                'content': review.content,
                'ai_sentiment': review.get_sentiment_display
            })
            
    return JsonResponse({'status': 'error', 'message': 'Không thể chỉnh sửa'}, status=400)

# --- HÀM XÓA BÌNH LUẬN ---
def delete_review(request, id):
    if request.method == "POST" and request.user.is_authenticated:
        # SỬA TẠI ĐÂY: Thay ProductReview bằng Review
        review = get_object_or_404(Review, id=id, user=request.user)
        review.delete()
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'status': 'error', 'message': 'Không thể xóa'}, status=400)


def apply_coupon_logic(request, order, coupon_code):
    try:
        promo = Promotion.objects.get(code=coupon_code, active=True)
    except Promotion.DoesNotExist:
        return False, "Mã giảm giá không tồn tại!", 0

    # 1. Check thời gian
    now = timezone.now()
    if promo.start_date > now or promo.end_date < now:
        return False, "Mã giảm giá đã hết hạn!", 0

    # 2. Check User (nếu model có hàm này)
    if hasattr(promo, 'is_valid_for_user') and not promo.is_valid_for_user(request.user):
        return False, "Mã này không dành cho bạn.", 0

    # 3. Tính toán trên sản phẩm hợp lệ
    eligible_amount = 0
    order_items = order.orderitem_set.all()
    has_valid_product = False

    # Check hàm is_valid_for_product
    check_product_scope = hasattr(promo, 'is_valid_for_product')

    for item in order_items:
        if check_product_scope:
            if promo.is_valid_for_product(item.product):
                has_valid_product = True
                eligible_amount += item.get_total
        else:
            has_valid_product = True
            eligible_amount += item.get_total

    if not has_valid_product:
        return False, "Không có sản phẩm nào phù hợp mã giảm giá.", 0

    # 4. Tính tiền giảm
    discount = 0
    if promo.is_percentage:
        discount = (eligible_amount * promo.discount_value) / 100
    else:
        discount = promo.discount_value

    # Không giảm quá số tiền hàng
    if discount > eligible_amount:
        discount = eligible_amount

    return True, "Áp dụng thành công!", discount


def promotion_policy(request):
    # Lấy số lượng promo đang active để hiển thị badge
    active_promos_count = Promotion.objects.filter(active=True).count()
    context = {'active_promos_count': active_promos_count}
    return render(request, 'app/promotion_policy.html', context)