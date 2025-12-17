from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import *
import json
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404
from .models import Product
from django.contrib.auth.decorators import login_required
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

def home(request):
    # XÓA LOGIC TÍNH TOÁN cartItems
    brands = Brand.objects.all()
    products = Product.objects.all() 
    # Chỉ truyền dữ liệu mà hàm home cần
    context= {'products': products, 'brands': brands}
    return render(request, 'app/home.html',context)

def cart(request):
    # XÓA LOGIC TÍNH TOÁN cartItems TẠI ĐÂY
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        # cartItems = order.get_cart_items # XÓA
    else:
        items = []
        order = {'get_cart_total':0, 'get_cart_items':0}
        # cartItems = order['get_cart_items'] # XÓA
    # Giữ lại 'order' và 'items' vì chúng được dùng trong template
    context= {'items': items, 'order': order} 
    return render(request, 'app/cart.html',context) 

def checkout(request):
    # XÓA LOGIC TÍNH TOÁN cartItems
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        # cartItems = order.get_cart_items # XÓA
    else:
        items = []
        order = {'get_cart_total':0, 'get_cart_items':0}
        # cartItems = order['get_cart_items'] # XÓA
    context= {'items': items, 'order': order}
    return render(request, 'app/checkout.html',context)

def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']    
    action = data['action']
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'User not authenticated'}, status=401)
        
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
        new_item_quantity = 0 
        new_item_total = 0 
    else:
        new_item_quantity = orderItem.quantity
        new_item_total = orderItem.get_total # Giả định OrderItem có thuộc tính get_total
        # Do get_total có thể trả về giá trị số (float/decimal), bạn nên format nó trong JS.
        # Hoặc format ở đây: new_item_total = f"{orderItem.get_total:,.0f}₫" 

    # Cập nhật đối tượng Order sau khi thay đổi OrderItem
    order.save() 

    new_cart_total_items = order.get_cart_items 
    new_cart_total_price = order.get_cart_total # Giả định Order có thuộc tính get_cart_total

    # Trả về JsonResponse chứa TẤT CẢ các giá trị cần cập nhật trên frontend
    return JsonResponse({
        'cart_total': new_cart_total_items,       
        'item_quantity': new_item_quantity,       
        'item_get_total': new_item_total,         
        'order_get_cart_total': new_cart_total_price, 
        'productId': productId
    }, safe=False)

def product_detail(request, pk): 
    product = get_object_or_404(Product, pk=pk)
    context = {'product': product}
    return render(request, 'app/product_detail.html', context)

# XÓA LOGIC TÍNH TOÁN cartItems
def user_info(request):
    context = {} # XÓA 'cartItems': cartItems
    return render(request, 'app/user_info.html', context)

# XÓA LOGIC TÍNH TOÁN cartItems
def about(request):
    context = {} # XÓA 'cartItems': cartItems
    return render(request, 'app/about.html', context)

def contact(request):
    # XÓA LOGIC TÍNH TOÁN cartItems
    message_success = False

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # Giả định Contact là model của bạn
        contact.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        message_success = True 

    context = {'success': message_success} # XÓA 'cartItems': cartItems
    return render(request, 'app/contact.html', context)

def product_list_by_brand(request, brand_slug):
    """
    Hiển thị danh sách sản phẩm thuộc một hãng cụ thể
    """
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