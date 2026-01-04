from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import *
import json
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404
from .models import Product
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth import logout
from django.db.models import Q
from django.db.models import Sum # Thêm import Sum nếu cần dùng tính tổng

@login_required(login_url='login')

# Create your views here.
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
        order = {'get_cart_total':0, 'get_cart_items':0}
        cartItems = order['get_cart_items']
    context= {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'app/checkout.html',context)

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

    # Truy vấn sản phẩm theo thương hiệu hiện tại
    products = Product.objects.filter(brand=current_brand)

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

    # 2. Lấy đối tượng Brand hiện tại bằng slug
    current_brand = get_object_or_404(Brand, slug=brand_slug)

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