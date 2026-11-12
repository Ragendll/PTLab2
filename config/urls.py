from django.contrib.auth import views as auth_views
from django.urls import path

from shop import views

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.add, name="add"),
    path("cart/remove/<int:product_id>/", views.remove, name="remove"),
    path("cart/checkout/", views.checkout, name="checkout"),
    path("orders/", views.orders, name="orders"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
