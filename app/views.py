from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import *
import json
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404
from .models import Product
from django.contrib.auth.decorators import login_required
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