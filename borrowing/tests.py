from datetime import datetime, timedelta, date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from borrowing.models import Borrowing, FINE_MULTIPLIER
from borrowing.serializers import BorrowingSerializer
from books.tests import sample_book
from payments.models import Payment

BORROWING_URL = reverse("borrowing:borrowing-list")


def sample_user():
    return get_user_model().objects.create_user(
        email="test@test.com", password="TestUser"
    )


def payload_for_borrowing(user: get_user_model(), **kwargs) -> dict:
    book = sample_book()
    borrow_date = timezone.now().date()
    payload = {
        "book": book,
        "borrow_date": borrow_date,
        "expected_return_date": borrow_date + timedelta(days=14),
        "user": user,
    }
    payload.update(kwargs)

    return payload


def sample_borrowing(user: get_user_model(), expected_return_date=None) -> Borrowing:
    if expected_return_date is None:
        expected_return_date = date.today() + timedelta(days=14)
    defaults = payload_for_borrowing(user, expected_return_date=expected_return_date)

    return Borrowing.objects.create(**defaults)


def detail_borrowing_url(borrowing_id: int):
    return reverse("borrowing:borrowing-detail", kwargs={"pk": borrowing_id})


class UnauthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauth_list(self):
        user = sample_user()
        sample_borrowing(user=user)

        res = self.client.get(BORROWING_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user()
        self.auth_user = get_user_model().objects.create_user(
            email="test2@test2.com",
            password="TestUser2",
        )
        self.client.force_authenticate(self.auth_user)

    def test_auth_borrowing_list(self):
        sample_borrowing(user=self.user)
        sample_borrowing(user=self.auth_user)

        borrowing = Borrowing.objects.filter(user=self.auth_user)
        res = self.client.get(BORROWING_URL)
        serializer = BorrowingSerializer(borrowing, many=True)

        self.assertEqual(res.data, serializer.data)

        all_borrowings = Borrowing.objects.all()
        serializer = BorrowingSerializer(all_borrowings, many=True)

        self.assertNotEqual(res.data, serializer.data)

    def test_auth_borrowing_create(self):
        book = sample_book()
        payload = payload_for_borrowing(self.auth_user, book=book.id)

        res = self.client.post(BORROWING_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_auth_borrowing_decrease_inventory_on_create(self):
        book = sample_book()  # "inventory": 10
        payload = payload_for_borrowing(self.auth_user, book=book.id)

        res = self.client.post(BORROWING_URL, payload)
        borrowing_id = res.data["id"]
        book_inventory = Borrowing.objects.get(id=borrowing_id).book.inventory

        self.assertEqual(book_inventory, 9)

    def test_auth_borrowing_increase_inventory_on_return(self):
        borrowing = sample_borrowing(user=self.auth_user)  # "inventory": 10
        return_url = reverse(
            "borrowing:borrowing-return-borrowing", args=[borrowing.id]
        )

        res = self.client.post(return_url)
        book_inventory = Borrowing.objects.get(id=borrowing.id).book.inventory

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(book_inventory, 11)

    def test_auth_other_user_borrowing_detail(self):
        borrowing = sample_borrowing(user=self.user)

        url = detail_borrowing_url(borrowing.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_auth_user_fine_payment_for_book_overdue(self):
        # expected_return_date = 14, actual_return_date 17, overdue_days = 3
        freeze_target = date.today() + timedelta(days=17)
        expected_return_date = freeze_target - timedelta(days=3)
        with freeze_time(freeze_target):
            borrowing = sample_borrowing(
                user=self.auth_user,
                expected_return_date=expected_return_date
            )
            return_url = reverse(
                "borrowing:borrowing-return-borrowing", args=[borrowing.id]
            )
            res = self.client.post(return_url)

            updated_borrowing = Borrowing.objects.get(id=borrowing.id)

            payment = Payment.objects.filter(
                borrowing=updated_borrowing.id, type=Payment.Type.FINE
            ).first()

            overdue_days = (
                    updated_borrowing.actual_return_date
                    - updated_borrowing.expected_return_date
            ).days
            overdue_price = (
                    overdue_days
                    * updated_borrowing.book.daily_fee
                    * Decimal(FINE_MULTIPLIER)
            )

            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(
                updated_borrowing.actual_return_date,
                freeze_target,
            )
            self.assertEqual(payment.money_to_pay, overdue_price)


class AdminBorrowingTestVew(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user()
        self.admin_user = get_user_model().objects.create_user(
            email="test1@test1.com",
            password="TestUser1",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin_user)

    def test_admin_borrowing_list(self):
        sample_borrowing(user=self.user)
        sample_borrowing(user=self.admin_user)

        borrowings = Borrowing.objects.all()
        serializer = BorrowingSerializer(borrowings, many=True)
        res = self.client.get(BORROWING_URL)

        self.assertEqual(res.data, serializer.data)

    def test_admin_other_user_borrowing_detail(self):
        borrowing = sample_borrowing(user=self.user)

        url = detail_borrowing_url(borrowing.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
