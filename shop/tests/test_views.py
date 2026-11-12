from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from shop import views
from shop.models import Order, Product


class CheckoutUnitTests(SimpleTestCase):
    @patch("shop.views.place_order")
    @patch("shop.views.cart_rows")
    def test_checkout_calls_order_service_and_clears_cart(self, rows, place):
        request = RequestFactory().post("/cart/checkout/")
        request.user = SimpleNamespace(is_authenticated=True)
        request.session = {"cart": {"1": 2}}
        rows.return_value = [(SimpleNamespace(name="Сидр"), 2)]

        response = views.checkout(request)

        rows.assert_called_once_with({"1": 2})
        place.assert_called_once_with(request.user, rows.return_value)
        self.assertNotIn("cart", request.session)
        self.assertEqual(response.url, reverse("orders"))

    @patch("shop.views.place_order")
    @patch("shop.views.cart_rows", return_value=[])
    def test_empty_checkout_does_not_call_order_service(self, rows, place):
        request = RequestFactory().post("/cart/checkout/")
        request.user = SimpleNamespace(is_authenticated=True)
        request.session = {}
        self.assertEqual(views.checkout(request).url, reverse("cart"))
        place.assert_not_called()


class ShopPagesTests(TestCase):
    fixtures = ["products"]

    @classmethod
    def setUpTestData(cls):
        cls.customer = get_user_model().objects.create_user(
            "buyer", password="Long!TestPass-208",
        )
        cls.product = Product.objects.get(pk=1)

    def test_catalog_displays_loaded_products(self):
        response = self.client.get(reverse("catalog"))
        self.assertContains(response, self.product.name)
        self.assertEqual(len(response.context["products"]), 4)

    def test_guest_cart_counts_multiple_copies_and_removes_one(self):
        add = reverse("add", args=[self.product.pk])
        remove = reverse("remove", args=[self.product.pk])
        cart = reverse("cart")
        for _ in range(2):
            self.assertRedirects(self.client.post(add), cart)
        response = self.client.get(cart)
        self.assertEqual(response.context["count"], 2)
        self.assertEqual(response.context["total"], Decimal("2100.00"))
        self.client.post(remove)
        self.assertEqual(self.client.get(cart).context["count"], 1)
        self.client.post(remove)
        self.assertContains(self.client.get(cart), "Корзина пуста")

    def test_missing_product_does_not_change_cart(self):
        self.assertEqual(self.client.post(reverse("add", args=[999])).status_code, 404)
        self.assertNotIn("cart", self.client.session)

    def test_get_cannot_change_cart(self):
        for name in ("add", "remove"):
            with self.subTest(name=name):
                url = reverse(name, args=[self.product.pk])
                self.assertEqual(self.client.get(url).status_code, 405)
        self.assertNotIn("cart", self.client.session)

    def test_login_is_required_for_history_and_checkout(self):
        self.assertRedirects(self.client.get(reverse("orders")),
                             "/login/?next=/orders/")
        self.assertRedirects(self.client.post(reverse("checkout")),
                             "/login/?next=/cart/checkout/")

    def test_registration_creates_account_and_logs_in(self):
        response = self.client.post(reverse("register"), {
            "username": "new_customer",
            "password1": "Long!PassWord-987",
            "password2": "Long!PassWord-987",
        })
        self.assertRedirects(response, reverse("catalog"))
        customer = get_user_model().objects.get(username="new_customer")
        self.assertEqual(self.client.session["_auth_user_id"], str(customer.pk))

    def test_invalid_registration_displays_errors(self):
        self.assertContains(self.client.get(reverse("register")), "Регистрация")
        response = self.client.post(reverse("register"), {
            "username": "buyer", "password1": "short", "password2": "other",
        })
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_guest_cart_survives_login_and_is_saved_as_order(self):
        self.client.post(reverse("add", args=[self.product.pk]))
        self.assertRedirects(self.client.post(reverse("login"), {
            "username": "buyer", "password": "Long!TestPass-208",
        }), reverse("catalog"))
        self.assertRedirects(self.client.post(reverse("checkout")), reverse("orders"))
        order = Order.objects.get(customer=self.customer)
        self.assertEqual(order.items.get().quantity, 1)
        self.assertEqual(order.total, self.product.price)
        self.assertNotIn("cart", self.client.session)
        self.assertContains(self.client.get(reverse("orders")), self.product.name)

    def test_history_shows_only_current_customers_orders(self):
        other = get_user_model().objects.create_user("other")
        own = Order.objects.create(customer=self.customer, total=Decimal("10.00"))
        Order.objects.create(customer=other, total=Decimal("20.00"))
        self.client.force_login(self.customer)
        response = self.client.get(reverse("orders"))
        self.assertQuerySetEqual(response.context["orders"], [own])

    def test_logout_ends_session(self):
        self.client.force_login(self.customer)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("catalog"))
        self.assertNotIn("_auth_user_id", self.client.session)
