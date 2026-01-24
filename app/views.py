import os
import re
import json
import hashlib
import hmac
import urllib.parse
import urllib.request
import random
from django.core.cache import cache
from .services.turnstile import verify_turnstile
from datetime import datetime, timedelta
from .services.ai_rating import recompute_product_ai_rating
from .services.aspect_aggregate import compute_overall_from_aspects
from .services.ai_client import analyze_sentiment_detailed
from .services.ai_client import analyze_sentiment
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .services.aspect_aggregate import aggregate_aspects

import requests
import joblib
from .models import Product, Review
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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
    PaymentForm,
    Store
)

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
        try:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            cartItems = order.get_cart_items
        except:
            cartItems = 0
    else:
        cartItems = 0

    products = Product.objects.order_by("-ai_rating", "-ai_rating_count")
    brands = Brand.objects.all()
    context= {'products': products, 'cartItems': cartItems, 'brands': brands}
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
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0, 'id': 0}
        messages.warning(request, "Vui lòng đăng nhập để thanh toán.")
        return redirect('login')
    selected_ids_str = request.GET.get('items')

    subtotal = order.get_cart_total if hasattr(order, 'get_cart_total') else 0
    if selected_ids_str:
        selected_ids = selected_ids_str.split(',')

        items = items.filter(product_id__in=selected_ids)


        subtotal = sum([item.get_total for item in items])
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
                vnp.requestData['vnp_Amount'] = int(final_total * 100)
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
            if promo.promotion_type == 'new_customer':
                return False, "Mã này chỉ dành cho khách hàng lần đầu mua sắm.", 0
            elif promo.promotion_type == 'vip':
                 return False, "Mã này chỉ dành cho khách hàng VIP (Chi tiêu trên 20tr).", 0
            else:
                return False, "Bạn không thuộc đối tượng áp dụng mã này.", 0

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


def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']
    customer = request.user.customer
    product = Product.objects.get(id = productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)
    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)
    orderItem = OrderItem.objects.filter(order=order, product=product).first()
    if action == 'add':
        orderItem.quantity += 1
    elif action == 'remove':
        orderItem.quantity -= 1
    elif action == 'delete':
        orderItem.quantity = 0
    orderItem.save()
    if orderItem.quantity <= 0:
        orderItem.delete()
    return JsonResponse('added', safe=False)
 # mua ngay
def buy_now(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        #xoa giỏ hàng hiện tại
        order.orderitem_set.all().delete()

        product = Product.objects.get(id=productId)
        OrderItem.objects.create(order=order, product=product, quantity=1)

        return JsonResponse('Cart cleared and item added', safe=False)
    else:
        return JsonResponse('User not logged in', safe=False)

def product_list_by_brand(request, brand_slug):
    brands = Brand.objects.all()
    current_brand = get_object_or_404(Brand, slug=brand_slug)
    products = Product.objects.filter(brand=current_brand)
    context = {
        'products': products,
        'brands': brands,
        'current_brand': current_brand,
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

def contact(request):
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
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        message_success = True
    context = {'cartItems': cartItems, 'success': message_success}
    return render(request, 'app/contact.html', context)

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

def promotion_policy(request):
    active_promos_count = Promotion.objects.filter(active=True).count()
    context = {'active_promos_count': active_promos_count}
    return render(request, 'app/promotion_policy.html', context)

#vnpay view demo
def index(request):
    return render(request, "payment/index.html", {"title": "Danh sách demo"})

def hmacsha512(key, data):
    byteKey = key.encode('utf-8')
    byteData = data.encode('utf-8')
    return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()


def payment(request):

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            order_type = form.cleaned_data['order_type']
            order_id = form.cleaned_data['order_id']
            amount = form.cleaned_data['amount']
            order_desc = form.cleaned_data['order_desc']
            bank_code = form.cleaned_data['bank_code']
            language = form.cleaned_data['language']
            ipaddr = get_client_ip(request)
            vnp = vnpay()
            vnp.requestData['vnp_Version'] = '2.1.0'
            vnp.requestData['vnp_Command'] = 'pay'
            vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
            vnp.requestData['vnp_Amount'] = amount * 100
            vnp.requestData['vnp_CurrCode'] = 'VND'
            vnp.requestData['vnp_TxnRef'] = order_id
            vnp.requestData['vnp_OrderInfo'] = order_desc
            vnp.requestData['vnp_OrderType'] = order_type
            if language and language != '':
                vnp.requestData['vnp_Locale'] = language
            else:
                vnp.requestData['vnp_Locale'] = 'vn'
            if bank_code and bank_code != "":
                vnp.requestData['vnp_BankCode'] = bank_code

            vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')
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

            firstTimeUpdate = True
            totalamount = True
            if totalamount:
                if firstTimeUpdate:
                    if vnp_ResponseCode == '00':
                        print('Payment Success. Your code implement here')
                    else:
                        print('Payment Error. Your code implement here')

                    result = JsonResponse({'RspCode': '00', 'Message': 'Confirm Success'})
                else:
                    result = JsonResponse({'RspCode': '02', 'Message': 'Order Already Update'})
            else:
                result = JsonResponse({'RspCode': '04', 'Message': 'invalid amount'})
        else:
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


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

n = random.randint(10**11, 10**12 - 1)
n_str = str(n)
while len(n_str) < 12:
    n_str = '0' + n_str


def query(request):
    if request.method == 'GET':
        return render(request, "payment/query.html", {"title": "Kiểm tra kết quả giao dịch"})

    url = settings.VNPAY_API_URL
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = settings.VNPAY_TMN_CODE
    vnp_Version = '2.1.0'

    vnp_RequestId = n_str
    vnp_Command = 'querydr'
    vnp_TxnRef = request.POST['order_id']
    vnp_OrderInfo = 'kiem tra gd'
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_IpAddr = get_client_ip(request)

    hash_data = "|".join([
        vnp_RequestId, vnp_Version, vnp_Command, vnp_TmnCode,
        vnp_TxnRef, vnp_TransactionDate, vnp_CreateDate,
        vnp_IpAddr, vnp_OrderInfo
    ])

    secure_hash = hmac.new(secret_key.encode(), hash_data.encode(), hashlib.sha512).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash

    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {"error": f"Request failed with status code: {response.status_code}"}

    return render(request, "payment/query.html", {"title": "Kiểm tra kết quả giao dịch", "response_json": response_json})

def refund(request):
    if request.method == 'GET':
        return render(request, "payment/refund.html", {"title": "Hoàn tiền giao dịch"})
    url = settings.VNPAY_API_URL
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = settings.VNPAY_TMN_CODE
    vnp_RequestId = n_str
    vnp_Version = '2.1.0'
    vnp_Command = 'refund'
    vnp_TransactionType = request.POST['TransactionType']
    vnp_TxnRef = request.POST['order_id']
    vnp_Amount = request.POST['amount']
    vnp_OrderInfo = request.POST['order_desc']
    vnp_TransactionNo = '0'
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_CreateBy = 'user01'
    vnp_IpAddr = get_client_ip(request)

    hash_data = "|".join([
        vnp_RequestId, vnp_Version, vnp_Command, vnp_TmnCode, vnp_TransactionType, vnp_TxnRef,
        vnp_Amount, vnp_TransactionNo, vnp_TransactionDate, vnp_CreateBy, vnp_CreateDate,
        vnp_IpAddr, vnp_OrderInfo
    ])

    secure_hash = hmac.new(secret_key.encode(), hash_data.encode(), hashlib.sha512).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_Amount": vnp_Amount,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_TransactionType": vnp_TransactionType,
        "vnp_TransactionNo": vnp_TransactionNo,
        "vnp_CreateBy": vnp_CreateBy,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {"error": f"Request failed with status code: {response.status_code}"}

    return render(request, "payment/refund.html", {"title": "Kết quả hoàn tiền giao dịch", "response_json": response_json})


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
    return render(request, 'app/product_search.html', context)
def order_history(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        orders = Order.objects.filter(customer=customer).order_by('-date_ordered')
        return render(request, 'app/order_history.html', {'orders': orders})
    else:
        return redirect('login')


@csrf_exempt
def absa_predict(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
        text = body.get("text", "").strip()

        if not text:
            return JsonResponse({"error": "empty text"}, status=400)

        results = predict_comment(text)

        return JsonResponse({
            "input": text,
            "results": [
                {"aspect": a, "sentiment": s}
                for a, s in results
            ]
        }, json_dumps_params={"ensure_ascii": False})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# def add_review(request, product_id):
#     if request.method != "POST":
#         return JsonResponse({"status": "error"}, status=405)

#     content = request.POST.get("content", "").strip()
#     honeypot = request.POST.get("honeypot", "")

#     if honeypot or not content:
#         return JsonResponse({"status": "spam"})

#     product = Product.objects.get(id=product_id)

#     # ===== AI CHẠY Ở ĐÂY =====
#     ai_result = predict_comment(content)

#     # MẶC ĐỊNH TRUNG LẬP
#     sentiment = None

#     for _, s in ai_result:
#         if s == "negative":
#             sentiment = 0
#             break
#         if s == "positive":
#             sentiment = 1

#     Review.objects.create(
#         product=product,
#         user=request.user,
#         content=content,
#         sentiment=sentiment
#     )

#     return JsonResponse({"status": "success"})


@login_required
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    product_reviews = product.reviews.select_related("user").all()

    aspect_stats = aggregate_aspects(product_reviews)
    ai_overall = compute_overall_from_aspects(aspect_stats)

    return render(request, "app/product_detail.html", {
        "product": product,
        "product_reviews": product_reviews,
        "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY,
        "aspect_stats": aspect_stats,
        "ai_overall": ai_overall,
    })


# --------------AI Model-----------------#
def analyze_view(request):
    text = request.GET.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "Thiếu nội dung"}, status=400)

    results = analyze_sentiment_detailed(text, threshold=0.3)
    return JsonResponse({"text": text, "results": results})

def absa_page(request):
    return render(request, "absa.html")

SPAM_URL_RE = re.compile(r"(https?://|www\.)", re.I)
SPAM_PHONE_RE = re.compile(r"(\+?\d[\d\-\s]{8,}\d)")
REPEAT_CHAR_RE = re.compile(r"(.)\1{6,}")  # 1 ký tự lặp >= 7

def is_spam_text(text: str) -> str | None:
    t = (text or "").strip()

    if len(t) < 6:
        return "Nội dung quá ngắn."
    if len(t) > 500:
        return "Nội dung quá dài."

    if SPAM_URL_RE.search(t):
        return "Không cho phép chèn link trong bình luận."
    if SPAM_PHONE_RE.search(t):
        return "Không cho phép chèn số điện thoại trong bình luận."
    if REPEAT_CHAR_RE.search(t):
        return "Nội dung có quá nhiều ký tự lặp."

    # quá nhiều ký tự đặc biệt
    non_alnum = sum(1 for c in t if not c.isalnum() and not c.isspace())
    if non_alnum / max(len(t), 1) > 0.35:
        return "Nội dung không hợp lệ."

    return None


def rate_limit_or_block(user_id: int, product_id: int, action: str, seconds: int) -> bool:
    """
    True = bị chặn
    """
    key = f"rl:review:{action}:{user_id}:{product_id}"
    if cache.get(key):
        return True
    cache.set(key, 1, seconds)
    return False


def duplicate_block(user_id: int, product_id: int, content: str, seconds: int = 120) -> bool:
    key = f"dup:review:{user_id}:{product_id}:{hash(content)}"
    if cache.get(key):
        return True
    cache.set(key, 1, seconds)
    return False


def add_review(request, product_id):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "Bạn cần đăng nhập"}, status=401)

    token = (request.POST.get("cf-turnstile-response") or "").strip()
    ok, err = verify_turnstile(token, request.META.get("REMOTE_ADDR"))
    if not token:
        return JsonResponse({"ok": False, "error": "Thiếu Turnstile token"}, status=400)

    # ok, err = verify_turnstile(token, request.META.get("REMOTE_ADDR"))
    # if not ok:
    #     return JsonResponse({"ok": False, "error": err}, status=400)

    # ===== Honeypot (bot hay điền) =====
    honeypot = (request.POST.get("honeypot") or "").strip()
    if honeypot:
        return JsonResponse({"ok": False, "error": "Spam detected"}, status=400)

    content = (request.POST.get("content") or "").strip()
    if not content:
        return JsonResponse({"ok": False, "error": "Thiếu nội dung"}, status=400)

    # ===== Rate limit: 1 comment / 15s / mỗi product =====
    if rate_limit_or_block(request.user.id, product_id, action="add", seconds=15):
        return JsonResponse({"ok": False, "error": "Bạn thao tác quá nhanh, thử lại sau vài giây."}, status=429)

    # ===== Lọc nội dung spam =====
    reason = is_spam_text(content)
    if reason:
        return JsonResponse({"ok": False, "error": reason}, status=400)

    # ===== Chặn trùng lặp trong 2 phút =====
    if duplicate_block(request.user.id, product_id, content, seconds=120):
        return JsonResponse({"ok": False, "error": "Bạn vừa gửi bình luận này rồi."}, status=400)

    product = get_object_or_404(Product, id=product_id)

    # 1) tạo review trước (ai_result tạm rỗng)
    review = Review.objects.create(
        product=product,
        user=request.user,
        content=content,
        ai_result=[],
    )

    # 2) gọi AI + lưu ai_result
    try:
        ai = analyze_sentiment_detailed(content, threshold=0.3)
    except Exception:
        ai = []

    review.ai_result = ai

    # 3) tính sentiment tổng quan từ ai_result
    review.set_sentiment_from_ai()

    # 4) save review
    review.save(update_fields=["ai_result", "sentiment"])

    # 5) cập nhật AI rating lưu vào Product
    ai_overall, cnt = recompute_product_ai_rating(product)
    product.ai_rating = ai_overall
    product.ai_rating_count = cnt
    product.save(update_fields=["ai_rating", "ai_rating_count"])

    # 6) Tính lại breakdown để trả về UI (KHÔNG cần reload)
    reviews = Review.objects.filter(product=product).select_related("user")
    aspect_stats = aggregate_aspects(reviews)  # hàm bạn đã có

    return JsonResponse({
        "ok": True,
        "review": {
            "id": review.id,
            "username": review.user.username,
            "content": review.content,
            "sentiment": review.sentiment,
            "ai_result": review.ai_result,
            "date_added": review.date_added.strftime("%d/%m/%Y %H:%M")
        },
        "ai_overall": product.ai_rating,
        "review_count": product.ai_rating_count,
        "aspect_stats": aspect_stats,
    })


@login_required
@require_POST
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if review.user_id != request.user.id:
        return JsonResponse({"ok": False, "error": "Không có quyền"}, status=403)

    product = review.product
    review.delete()

    reviews = Review.objects.filter(product=product).select_related("user")
    aspect_stats = aggregate_aspects(reviews)
    ai_overall = compute_overall_from_aspects(aspect_stats)

    return JsonResponse({
        "ok": True,
        "id": review_id,
        "ai_overall": ai_overall,
        "aspect_stats": aspect_stats,
    })

@login_required
@require_POST
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    token = (request.POST.get("cf-turnstile-response") or "").strip()
    ok, err = verify_turnstile(token, request.META.get("REMOTE_ADDR"))
    if not token:
        return JsonResponse({"ok": False, "error": "Thiếu Turnstile token"}, status=400)


    if review.user_id != request.user.id:
        return JsonResponse({"ok": False, "error": "Không có quyền"}, status=403)

    content = (request.POST.get("content") or "").strip()
    if not content:
        return JsonResponse({"ok": False, "error": "Nội dung trống"}, status=400)

    product_id = review.product_id

    # ===== Rate limit: 1 edit / 10s / mỗi product =====
    if rate_limit_or_block(request.user.id, product_id, action="edit", seconds=10):
        return JsonResponse({"ok": False, "error": "Bạn sửa quá nhanh, thử lại sau vài giây."}, status=429)

    # ===== Lọc nội dung spam =====
    reason = is_spam_text(content)
    if reason:
        return JsonResponse({"ok": False, "error": reason}, status=400)

    # ===== Chặn trùng lặp (sửa không đổi gì) =====
    if content == (review.content or "").strip():
        return JsonResponse({"ok": False, "error": "Nội dung không thay đổi."}, status=400)

    # chạy lại AI cho nội dung mới
    try:
        ai_result = analyze_sentiment_detailed(content, threshold=0.3)
    except Exception:
        ai_result = []

    review.content = content
    review.ai_result = ai_result
    review.set_sentiment_from_ai()
    review.save(update_fields=["content", "ai_result", "sentiment"])

    # cập nhật AI rating lưu vào Product
    product = review.product
    ai_overall, cnt = recompute_product_ai_rating(product)
    product.ai_rating = ai_overall
    product.ai_rating_count = cnt
    product.save(update_fields=["ai_rating", "ai_rating_count"])

    # tính lại thống kê breakdown để trả về UI
    reviews = Review.objects.filter(product=product).select_related("user")
    aspect_stats = aggregate_aspects(reviews)

    return JsonResponse({
        "ok": True,
        "review": {
            "id": review.id,
            "content": review.content,
            "sentiment": review.sentiment,
            "ai_result": review.ai_result,
        },
        "ai_overall": product.ai_rating,
        "aspect_stats": aspect_stats,
    })
def store_list(request):
    stores = [
        {
            'name': 'Đại học Nông Lâm TP.HCM',
            'address': 'VQCR+GP6, khu phố 6, Thủ Đức, TP. Hồ Chí Minh',
            'phone': '0123456789',
            'latitude': 10.8712764,
            'longitude': 106.7917617,
            # Link embed Google Maps cho địa chỉ này
            'map_url': "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3918.2541344440056!2d106.7891867757366!3d10.87128165749005!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3174d86698969f7b%3A0x9672b7efd0893fc4!2zVHLGsOG7nW5nIMSQ4bqhaSBo4buNYyBOw7RuZyBMw6JtIFRQLiBI4buTIENow60gTWluaA!5e0!3m2!1svi!2s!4v1700000000000!5m2!1vi!2s"
        }
    ]
    return render(request, 'app/store_list.html', {'stores': stores})