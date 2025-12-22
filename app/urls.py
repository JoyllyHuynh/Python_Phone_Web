from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('cart/', views.cart, name='cart'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('checkout/', views.checkout, name='checkout'),
    path('update_item/', views.updateItem, name='update_item'),
    path('product-detail/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<slug:brand_slug>/', views.product_list_by_brand, name='product_list_by_brand'),
    path('user_info/', views.user_info, name='user_info'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('product_seach/', views.product_seach, name='product_seach'),
]
