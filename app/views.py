
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


try:
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTOR_PATH)
except Exception as e:
    print(f"Lỗi AI: {e}")
    model = vectorizer = None

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST" and request.user.is_authenticated:
        if request.POST.get('honeypot'):
            return JsonResponse({'status': 'error', 'message': 'Phát hiện hành vi spam!'}, status=400)

        content = request.POST.get('content', '').strip()

        if len(content) < 5:
            return JsonResponse({'status': 'error', 'message': 'Bình luận quá ngắn (tối thiểu 5 ký tự).'}, status=400)

        blacklist = ['http', 'www', '.com', '.vn', 'zalo', '09', 'kiếm tiền', 'nhận quà', 'click vào']
        if any(word in content.lower() for word in blacklist):
            return JsonResponse({'status': 'error', 'message': 'Bình luận chứa liên kết hoặc từ ngữ quảng cáo bị cấm.'}, status=400)

        last_review = Review.objects.filter(user=request.user).order_by('-date_added').first()
        if last_review:
            time_diff = timezone.now() - last_review.date_added
            if time_diff < timedelta(seconds=30):
                return JsonResponse({'status': 'error', 'message': 'Bạn đang gửi quá nhanh. Vui lòng đợi một chút.'}, status=400)
            if content.lower() == last_review.content.lower():
                return JsonResponse({'status': 'error', 'message': 'Bạn đã gửi nội dung này trước đó.'}, status=400)

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