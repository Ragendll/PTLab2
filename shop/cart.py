from decimal import Decimal

from django.db import transaction

from .models import Order, OrderItem, Product


def cart_rows(quantities):
    products = Product.objects.in_bulk(quantities.keys())
    return [
        (products[int(key)], quantity)
        for key, quantity in quantities.items()
        if int(key) in products
    ]


def totals(rows):
    count = sum(quantity for _, quantity in rows)
    price = sum((product.price * quantity for product, quantity in rows),
                Decimal("0.00"))
    return count, price


def place_order(customer, rows):
    if not rows:
        raise ValueError("Корзина пуста")
    _, total = totals(rows)
    with transaction.atomic():
        order = Order.objects.create(customer=customer, total=total)
        OrderItem.objects.bulk_create([
            OrderItem(order=order, name=product.name, price=product.price,
                      quantity=quantity)
            for product, quantity in rows
        ])
    return order
