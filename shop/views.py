from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import cart_rows, place_order, totals
from .models import Order, Product


def catalog(request):
    return render(request, "shop/catalog.html", {
        "products": Product.objects.order_by("name"),
    })


def cart(request):
    rows = cart_rows(request.session.get("cart", {}))
    count, total = totals(rows)
    return render(request, "shop/cart.html", {
        "rows": rows, "count": count, "total": total,
    })


@require_POST
def add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    quantities = request.session.get("cart", {})
    key = str(product.pk)
    quantities[key] = quantities.get(key, 0) + 1
    request.session["cart"] = quantities
    return redirect("cart")


@require_POST
def remove(request, product_id):
    quantities = request.session.get("cart", {})
    key = str(product_id)
    if quantities.get(key, 0) > 1:
        quantities[key] -= 1
    else:
        quantities.pop(key, None)
    request.session["cart"] = quantities
    return redirect("cart")


@login_required
@require_POST
def checkout(request):
    rows = cart_rows(request.session.get("cart", {}))
    if not rows:
        return redirect("cart")
    place_order(request.user, rows)
    request.session.pop("cart", None)
    return redirect("orders")


@login_required
def orders(request):
    history = (Order.objects.filter(customer=request.user)
               .prefetch_related("items").order_by("-created_at"))
    return render(request, "shop/orders.html", {"orders": history})


def register(request):
    form = UserCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("catalog")
    return render(request, "registration/register.html", {"form": form})
