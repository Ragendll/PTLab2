from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from shop.cart import cart_rows, place_order, totals
from shop.models import Order, Product


class CartUnitTests(SimpleTestCase):
    def test_total_counts_units_instead_of_positions(self):
        rows = [(SimpleNamespace(price=Decimal("10.05")), 3),
                (SimpleNamespace(price=Decimal("2.10")), 2)]
        self.assertEqual(totals(rows), (5, Decimal("34.35")))

    def test_empty_cart(self):
        self.assertEqual(totals([]), (0, Decimal("0.00")))
        with self.assertRaisesMessage(ValueError, "Корзина пуста"):
            place_order(None, [])

    @patch("shop.cart.Product.objects.in_bulk")
    def test_rows_skip_missing_products(self, in_bulk):
        product = SimpleNamespace(pk=7)
        in_bulk.return_value = {7: product}
        quantities = {"7": 3, "10": 2}
        self.assertEqual(cart_rows(quantities), [(product, 3)])
        self.assertEqual(list(in_bulk.call_args.args[0]), ["7", "10"])


class OrderTests(TestCase):
    def setUp(self):
        self.customer = get_user_model().objects.create_user("buyer")
        self.product = Product.objects.create(
            name="Сидр", description="Яблочный", price=Decimal("110.50"),
        )

    def test_order_keeps_original_name_and_price(self):
        order = place_order(self.customer, [(self.product, 2)])
        self.product.name = "Новый сидр"
        self.product.price = Decimal("210.00")
        self.product.save()
        item = order.items.get()
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.total, Decimal("221.00"))
        self.assertEqual((item.name, item.price, item.quantity),
                         ("Сидр", Decimal("110.50"), 2))

    @patch("shop.cart.OrderItem.objects.bulk_create", side_effect=RuntimeError)
    def test_error_saving_items_rolls_back_order(self, bulk_create):
        with self.assertRaises(RuntimeError):
            place_order(self.customer, [(self.product, 2)])
        self.assertFalse(Order.objects.exists())
