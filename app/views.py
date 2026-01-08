
print(">>> USING ABSA PREDICTOR <<<")
from app.ai.absa.predictor import predict_comment

import os
import re
import json
import hashlib
import hmac
import urllib.parse
import urllib.request
import random
from datetime import datetime, timedelta

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from app.ai.absa.hybrid import predict_comment_hybrid as predict_comment

import requests
import joblib
from app.ai.absa.predictor import predict_comment
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
    PaymentForm    
)

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
        try:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            cartItems = order.get_cart_items
        except:
            cartItems = 0
    else:
        cartItems = 0

    products = Product.objects.all()
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

def add_review(request, product_id):
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=405)

    content = request.POST.get("content", "").strip()
    honeypot = request.POST.get("honeypot", "")

    if honeypot or not content:
        return JsonResponse({"status": "spam"})

    product = Product.objects.get(id=product_id)

    # ===== AI CHẠY Ở ĐÂY =====
    ai_result = predict_comment(content)

    # MẶC ĐỊNH TRUNG LẬP
    sentiment = None

    for _, s in ai_result:
        if s == "negative":
            sentiment = 0
            break
        if s == "positive":
            sentiment = 1

    Review.objects.create(
        product=product,
        user=request.user,
        content=content,
        sentiment=sentiment
    )

    return JsonResponse({"status": "success"})


@login_required
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    product_reviews = product.reviews.select_related("user").all()

    # ===== XỬ LÝ GỬI BÌNH LUẬN =====
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        honeypot = request.POST.get("honeypot", "")

        # anti-spam / empty
        if honeypot or not content:
            return JsonResponse({"status": "spam"})

        # ===== AI PREDICT =====
        ai_result = predict_comment(content)
        # ví dụ: [('man_hinh','positive'), ('nhiet_do','negative')]

        # ===== SENTIMENT TỔNG (để filter) =====
        # ƯU TIÊN: negative > positive > neutral
        sentiments = [s for _, s in ai_result]

        if "negative" in sentiments:
            sentiment = 0
        elif "positive" in sentiments:
            sentiment = 1
        else:
            sentiment = None

        # ===== LƯU REVIEW =====
        Review.objects.create(
            product=product,
            user=request.user,
            content=content,
            sentiment=sentiment,
            ai_result=ai_result  # 🔥 GIỮ NGUYÊN LIST NHIỀU ASPECT
        )

        return JsonResponse({"status": "success"})

    return render(request, "app/product_detail.html", {
        "product": product,
        "product_reviews": product_reviews
    })

@login_required
@require_POST
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    # chỉ cho phép chủ bình luận
    if review.user != request.user:
        return JsonResponse({"status": "forbidden"}, status=403)

    review.delete()
    return JsonResponse({"status": "success"})

@login_required
@require_POST
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if review.user != request.user:
        return JsonResponse({"status": "forbidden"}, status=403)

    content = request.POST.get("content", "").strip()
    if not content:
        return JsonResponse({"status": "error"}, status=400)

    # 👉 CHẠY LẠI AI
    ai_result = predict_comment(content)

    # sentiment tổng
    sentiments = [s for _, s in ai_result]
    if "negative" in sentiments:
        sentiment = 0
    elif "positive" in sentiments:
        sentiment = 1
    else:
        sentiment = None

    # cập nhật
    review.content = content
    review.ai_result = ai_result
    review.sentiment = sentiment
    review.save()

    return JsonResponse({
        "status": "success",
        "content": content,
        "ai_result": ai_result
    })
