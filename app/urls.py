from django.contrib import admin
from django.urls import path
from app import views
from .views import absa_predict
from django.contrib import admin


urlpatterns = [
    path('', views.home, name='home'),
    path('cart/', views.cart, name='cart'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_views, name='logout'),
    path('checkout/', views.checkout, name='checkout'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('update_item/', views.updateItem, name='update_item'),
    path('product-detail/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<slug:brand_slug>/', views.product_list_by_brand, name='product_list_by_brand'),
    path('user_info/', views.user_info, name='user_info'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('promotions/', views.promotion_list, name='promotion_list'),
    path('promotion-policy/', views.promotion_policy, name='promotion_policy'),
    path('product-search/', views.product_search, name='product_search'),
    path("predict/", absa_predict, name="absa_predict"),
    path("product/<int:product_id>/review/", views.add_review, name="add_review"),
    path("product/<int:id>/", views.product_detail, name="product_detail"),
    path("edit-review/<int:review_id>/", views.edit_review, name="edit_review"),
    path("delete-review/<int:review_id>/", views.delete_review, name="delete_review"),
    #path('payment_return/', views.payment_return, name='payment_return'),


    #vnpay urls
    path('pay',views.index, name='index'),
    path('payment', views.payment, name='payment'),
    path('payment_ipn', views.payment_ipn, name='payment_ipn'),
    path('payment_return', views.payment_return, name='payment_return'),
    path('query', views.query, name='query'),
    path('refund', views.refund, name='refund'),
   # path('admin/', admin.site.urls),
]
