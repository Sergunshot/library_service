from datetime import datetime, timedelta, date
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from payments.models import Payment
from payments.serializers import PaymentSerializer
from borrowing.tests import sample_user, sample_borrowing, BORROWING_URL
from books.tests import sample_book


PAYMENT_URL = reverse("payment:payment-list")


def payload_for_payment(user: get_user_model(), **kwargs) -> dict:
    borrowing = sample_borrowing(user)
    payload = {
        "status": Payment.Status.PENDING,
        "type": Payment.Type.PAYMENT,
        "borrowing": borrowing,
        "session_url": "test_url",
        "session_id": "test_id",
        "money_to_pay": 1,
    }
    payload.update(kwargs)

    return payload


def detail_payment_url(payment_id: int):
    return reverse("payment:payment-detail", kwargs={"pk": payment_id})


def sample_payment(user: get_user_model()) -> Payment:
    borrowing = sample_borrowing(user=user)
    defaults = payload_for_payment(user)
    defaults["borrowing"] = borrowing
    return Payment.objects.create(**defaults)


class MockedStripeCheckoutSessionRetrieve:
    def __init__(self, session_id: str):
        self.session_id = session_id

    @staticmethod
    def get(payment_status: str):
        return "paid"


class UnauthenticatedPaymentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauth_list(self):
        user = sample_user()
        sample_borrowing(user=user)

        res = self.client.get(PAYMENT_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserPaymentTestView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user()
        self.auth_user = get_user_model().objects.create_user(
            email="test2@test2.com",
            password="TestUser2",
        )
        self.client.force_authenticate(self.auth_user)

    def test_auth_payment_list(self):
        sample_payment(self.user)
        sample_payment(self.auth_user)

        payment = Payment.objects.filter(borrowing__user=self.auth_user)
        res = self.client.get(PAYMENT_URL)
        serializer = PaymentSerializer(payment, many=True)

        self.assertEqual(res.data, serializer.data)

        all_payments = Payment.objects.all()
        serializer = PaymentSerializer(all_payments, many=True)

        self.assertNotEqual(res.data, serializer.data)

    def test_auth_user_create_payment_from_borrowing(self):
        book = sample_book()
        payload = {
            "book": book.id,
            "expected_return_date": date.today() + timedelta(days=1),
        }
        res = self.client.post(BORROWING_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 1)

    def test_auth_other_user_payment_detail(self):
        payment = sample_payment(self.user)

        url = detail_payment_url(payment.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @patch("stripe.checkout.Session.retrieve", MockedStripeCheckoutSessionRetrieve)
    def test_auth_user_success_payment(self):
        payment = sample_payment(self.auth_user)
        query_params = {"session_id": payment.session_id}
        success_url = reverse("payment:payment-success")

        res = self.client.get(success_url + "?" + urlencode(query_params))
        updated_payment = Payment.objects.get(id=payment.id)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(updated_payment.status, Payment.Status.PAID)

    @patch("stripe.checkout.Session.retrieve", MockedStripeCheckoutSessionRetrieve)
    def test_auth_user_success_payment_already_done(self):
        payment = sample_payment(self.auth_user)
        query_params = {"session_id": payment.session_id}
        success_url = reverse("payment:payment-success")

        res = self.client.get(success_url + "?" + urlencode(query_params))
        updated_payment = Payment.objects.get(id=payment.id)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(updated_payment.status, Payment.Status.PAID)

        res2 = self.client.get(success_url + "?" + urlencode(query_params))

        self.assertEqual(res2.status_code, status.HTTP_404_NOT_FOUND)

    def test_auth_user_cancel_payment(self):
        payment = sample_payment(self.auth_user)
        query_params = {"session_id": payment.session_id}
        cancel_url = reverse("payment:payment-cancel")

        res = self.client.get(cancel_url + "?" + urlencode(query_params))
        updated_payment = Payment.objects.get(id=payment.id)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(updated_payment.status, Payment.Status.PENDING)


class AdminPaymentTestVew(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user()
        self.admin_user = get_user_model().objects.create_user(
            email="test1@test1.com",
            password="TestUser1",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin_user)

    def test_admin_payment_list(self):
        sample_payment(user=self.user)
        sample_payment(user=self.admin_user)

        all_payments = Payment.objects.all()
        serializer = PaymentSerializer(all_payments, many=True)
        res = self.client.get(PAYMENT_URL)

        self.assertEqual(res.data, serializer.data)

    def test_admin_other_user_payment_detail(self):
        payment = sample_payment(user=self.user)

        url = detail_payment_url(payment.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
