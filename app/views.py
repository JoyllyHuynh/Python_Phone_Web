
import os
import re
import json
import hashlib
import hmac
import urllib.parse
import urllib.request
import random
from datetime import datetime, timedelta

import requests
import joblib


from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q, Sum
from django.contrib import messages
from django.contrib.humanize.templatetags.humanize import intcomma


from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


from .vnpay import vnpay
from .models import (
    Product,
    Review,
    Customer,
    Promotion,
    Brand,
    Order,
    OrderItem,
    ShippingAddress,
    Payment_VNPay, 
    PaymentForm    
)

MODEL_PATH = os.path.join(settings.BASE_DIR, 'app', 'model_data', 'model_cam_xuc.pkl')
VECTOR_PATH = os.path.join(settings.BASE_DIR, 'app', 'model_data', 'vectorizer.pkl')

# --- AUTHENTICATION VIEWS ---
def register(request):
    form = UserCreationForm()
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
    context= {'form': form}
    return render(request, 'app/register.html',context)
def login(request):
    context= {}
    return render(request, 'app/login.html',context)
def logout_views(request):
    logout(request)
    return redirect('home')

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
        cartItems = order.get_cart_items
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0, 'id': 0}
        messages.warning(request, "Vui lòng đăng nhập để thanh toán.")
        return redirect('login')

    subtotal = order.get_cart_total if hasattr(order, 'get_cart_total') else 0
    shipping_fee = 0 if subtotal >= 2000000 else 30000
    if subtotal == 0: shipping_fee = 0

    discount_amount = 0
    coupon_code = request.session.get('coupon_code')
    if coupon_code:
        success, msg, real_discount = apply_coupon_logic(request, order, coupon_code)
        if success:
            discount_amount = real_discount
        else:
            del request.session['coupon_code']
            if 'coupon_discount' in request.session: del request.session['coupon_discount']

    final_total = subtotal + shipping_fee - discount_amount
    if final_total < 0: final_total = 0

    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            city = request.POST.get('city')
            district = request.POST.get('district')
            ward = request.POST.get('ward')
            note = request.POST.get('note')
            payment_method = request.POST.get('payment_method')

            full_address = f"{address}, {ward}, {district}, {city}"

            ShippingAddress.objects.create(
                customer=customer,
                order=order,
                address=full_address,
                city=city,
                state=district,
                phone_number=phone
            )

            if payment_method == 'vnpay':
                order_type = 'billpayment'
                order_desc = f'Thanh toan don hang {order.id}'
                language = 'vn'
                ipaddr = get_client_ip(request)

                txn_ref = f"{order.id}_{int(datetime.now().timestamp())}"
                
                order.transaction_id = txn_ref
                order.save()

                vnp = vnpay()
                vnp.requestData['vnp_Version'] = '2.1.0'
                vnp.requestData['vnp_Command'] = 'pay'
                vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
                vnp.requestData['vnp_Amount'] = int(final_total * 100) #
                vnp.requestData['vnp_CurrCode'] = 'VND'
                vnp.requestData['vnp_TxnRef'] = txn_ref
                vnp.requestData['vnp_OrderInfo'] = order_desc
                vnp.requestData['vnp_OrderType'] = order_type
                vnp.requestData['vnp_Locale'] = language
                vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')
                vnp.requestData['vnp_IpAddr'] = ipaddr
                vnp.requestData['vnp_ReturnUrl'] = settings.VNPAY_RETURN_URL
                
                vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY)
                
                return redirect(vnpay_payment_url)

            else:
                order.complete = True
                order.save()

                if 'coupon_code' in request.session: del request.session['coupon_code']
                if 'coupon_discount' in request.session: del request.session['coupon_discount']

                messages.success(request, "Đặt hàng thành công!")
                return redirect('home')

        except Exception as e:
            messages.error(request, f"Có lỗi xảy ra: {e}")
            return redirect('checkout')

    context = {
        'items': items,
        'order': order,
        'shipping_fee': shipping_fee,
        'discount_amount': discount_amount,
        'final_total': final_total,
        'coupon_code': coupon_code
    }
    return render(request, 'app/checkout.html', context)



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

def apply_coupon_logic(request, order, coupon_code):
    try:
        promo = Promotion.objects.get(code=coupon_code, active=True)
    except Promotion.DoesNotExist:
        return False, "Mã giảm giá không tồn tại!", 0

    now = timezone.now()
    if promo.start_date > now or promo.end_date < now:
        return False, "Mã giảm giá đã hết hạn!", 0

    if hasattr(promo, 'is_valid_for_user') and not promo.is_valid_for_user(request.user):
        return False, "Mã này không dành cho bạn.", 0

    eligible_amount = 0
    order_items = order.orderitem_set.all()
    has_valid_product = False
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

    discount = 0
    if promo.is_percentage:
        discount = (eligible_amount * promo.discount_value) / 100
    else:
        discount = promo.discount_value

    if discount > eligible_amount:
        discount = eligible_amount

    return True, "Áp dụng thành công!", discount

# --- OTHER FEATURES ---

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

def product_detail(request, pk): # Tên hàm phải khớp với tên trong urls.py
    product = get_object_or_404(Product, pk=pk)
    # Thêm logic xử lý bình luận, cấu hình, v.v.
    context = {'product': product}
    return render(request, 'app/product_detail.html', context)

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
    # Lấy thông tin thương hiệu hiện tại
    current_brand = Brand.objects.get(slug=brand_slug)

    # Lấy tất cả danh mục và các lựa chọn liên quan để hiển thị bộ lọc
    categories = Category.objects.all()

    # Lấy query parameters từ URL (nếu người dùng chọn bộ lọc)
    selected_categories = request.GET.getlist('category')  # Danh mục chọn
    selected_options = request.GET.getlist('option')  # Tùy chọn chọn

def edit_review(request, id):
    if request.method == "POST" and request.user.is_authenticated:
        review = get_object_or_404(Review, id=id, user=request.user)
        new_content = request.POST.get('content', '').strip()

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

def delete_review(request, id):
    if request.method == "POST" and request.user.is_authenticated:
        review = get_object_or_404(Review, id=id, user=request.user)
        review.delete()
        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error', 'message': 'Không thể xóa'}, status=400)



    # Lọc theo các danh mục đã chọn (nếu có)
    if selected_categories:
        products = products.filter(category__slug__in=selected_categories)

    # Lọc theo các tùy chọn đã chọn (nếu có)
    if selected_options:
        products = products.filter(options__slug__in=selected_options)

    # Loại bỏ các sản phẩm trùng lặp khi áp dụng nhiều bộ lọc
    products = products.distinct()

    # 1. Lấy tất cả các hãng để hiển thị sidebar/menu
    brands = Brand.objects.all()

    if request.method == 'POST':
        # Process input data and build url payment
        form = PaymentForm(request.POST)
        if form.is_valid():
            order_type = form.cleaned_data['order_type']
            order_id = form.cleaned_data['order_id']
            amount = form.cleaned_data['amount']
            order_desc = form.cleaned_data['order_desc']
            bank_code = form.cleaned_data['bank_code']
            language = form.cleaned_data['language']
            ipaddr = get_client_ip(request)
            # Build URL Payment
            vnp = vnpay()
            vnp.requestData['vnp_Version'] = '2.1.0'
            vnp.requestData['vnp_Command'] = 'pay'
            vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
            vnp.requestData['vnp_Amount'] = amount * 100
            vnp.requestData['vnp_CurrCode'] = 'VND'
            vnp.requestData['vnp_TxnRef'] = order_id
            vnp.requestData['vnp_OrderInfo'] = order_desc
            vnp.requestData['vnp_OrderType'] = order_type
            # Check language, default: vn
            if language and language != '':
                vnp.requestData['vnp_Locale'] = language
            else:
                vnp.requestData['vnp_Locale'] = 'vn'
                # Check bank_code, if bank_code is empty, customer will be selected bank on VNPAY
            if bank_code and bank_code != "":
                vnp.requestData['vnp_BankCode'] = bank_code

            vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')  # 20150410063022
            vnp.requestData['vnp_IpAddr'] = ipaddr
            vnp.requestData['vnp_ReturnUrl'] = settings.VNPAY_RETURN_URL
            vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY)
            print(vnpay_payment_url)
            return redirect(vnpay_payment_url)
        else:
            print("Form input not validate")
    else:
        return render(request, "payment/payment.html", {"title": "Thanh toán"})


def payment_ipn(request):
    inputData = request.GET
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.dict()
        order_id = inputData['vnp_TxnRef']
        amount = inputData['vnp_Amount']
        order_desc = inputData['vnp_OrderInfo']
        vnp_TransactionNo = inputData['vnp_TransactionNo']
        vnp_ResponseCode = inputData['vnp_ResponseCode']
        vnp_TmnCode = inputData['vnp_TmnCode']
        vnp_PayDate = inputData['vnp_PayDate']
        vnp_BankCode = inputData['vnp_BankCode']
        vnp_CardType = inputData['vnp_CardType']
        if vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            # Check & Update Order Status in your Database
            # Your code here
            firstTimeUpdate = True
            totalamount = True
            if totalamount:
                if firstTimeUpdate:
                    if vnp_ResponseCode == '00':
                        print('Payment Success. Your code implement here')
                    else:
                        print('Payment Error. Your code implement here')

                    # Return VNPAY: Merchant update success
                    result = JsonResponse({'RspCode': '00', 'Message': 'Confirm Success'})
                else:
                    # Already Update
                    result = JsonResponse({'RspCode': '02', 'Message': 'Order Already Update'})
            else:
                # invalid amount
                result = JsonResponse({'RspCode': '04', 'Message': 'invalid amount'})
        else:
            # Invalid Signature
            result = JsonResponse({'RspCode': '97', 'Message': 'Invalid Signature'})
    else:
        result = JsonResponse({'RspCode': '99', 'Message': 'Invalid request'})

    return result


def payment_return(request):
    inputData = request.GET
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.dict()
        order_id = inputData['vnp_TxnRef']
        amount = int(inputData['vnp_Amount']) / 100
        order_desc = inputData['vnp_OrderInfo']
        vnp_TransactionNo = inputData['vnp_TransactionNo']
        vnp_ResponseCode = inputData['vnp_ResponseCode']
        vnp_TmnCode = inputData['vnp_TmnCode']
        vnp_PayDate = inputData['vnp_PayDate']
        vnp_BankCode = inputData['vnp_BankCode']
        vnp_CardType = inputData['vnp_CardType']

        payment = Payment_VNPay.objects.create(
            order_id=order_id,
            amount=amount,
            order_desc=order_desc,
            vnp_TransactionNo=vnp_TransactionNo,
            vnp_ResponseCode=vnp_ResponseCode


        )

        if vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            if vnp_ResponseCode == "00":
                return render(request, "payment/payment_return.html", {"title": "Kết quả thanh toán",
                                                               "result": "Thành công", "order_id": order_id,
                                                               "amount": amount,
                                                               "order_desc": order_desc,
                                                               "vnp_TransactionNo": vnp_TransactionNo,
                                                               "vnp_ResponseCode": vnp_ResponseCode})
            else:
                return render(request, "payment/payment_return.html", {"title": "Kết quả thanh toán",
                                                               "result": "Lỗi", "order_id": order_id,
                                                               "amount": amount,
                                                               "order_desc": order_desc,
                                                               "vnp_TransactionNo": vnp_TransactionNo,
                                                               "vnp_ResponseCode": vnp_ResponseCode})
        else:
            return render(request, "payment/payment_return.html",
                          {"title": "Kết quả thanh toán", "result": "Lỗi", "order_id": order_id, "amount": amount,
                           "order_desc": order_desc, "vnp_TransactionNo": vnp_TransactionNo,
                           "vnp_ResponseCode": vnp_ResponseCode, "msg": "Sai checksum"})
    else:
        return render(request, "payment/payment_return.html", {"title": "Kết quả thanh toán", "result": ""})

    # 3. Lọc tất cả sản phẩm thuộc hãng này
    products = Product.objects.filter(brand=current_brand)

    context = {
        'products': products,
        'brands': brands,
        'current_brand': current_brand,
        'categories': categories,
        'selected_categories': selected_categories,
        'selected_options': selected_options,
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
def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    suggestions = Product.objects.filter(name__icontains=query)[:10]  # Gợi ý 10 sản phẩm
    response = [{'id': product.id, 'name': product.name} for product in suggestions]
    return JsonResponse(response, safe=False)
def product_search(request):
    query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'relevance')

    products = Product.objects.filter(name__icontains=query)

    if sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'price_asc':
        products = products.order_by('price')

    context = {
        'products': products,
        'q': query,
        'sort': sort,
    }
    return render(request, 'product_search.html', context)