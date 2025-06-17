from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from books.models import Book
from books.serializers import BookSerializer


BOOK_URL = reverse("books:book-list")

book_defaults = {
    "title": "title",
    "author": "author",
    "cover": "hard",
    "inventory": 10,
    "daily_fee": 1.5,
}


def sample_book(**params) -> Book:
    defaults = book_defaults
    defaults.update(params)
    return Book.objects.create(**defaults)


class UnauthenticatedBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauth_book_list(self):
        sample_book()
        sample_book()

        res = self.client.get(BOOK_URL)
        queryset = Book.objects.all()
        serializer = BookSerializer(queryset, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 2)

    def test_unauth_book_detail(self):
        book = sample_book()
        url = reverse("books:book-detail", args=[book.id])
        res = self.client.get(url)
        queryset = Book.objects.filter(id=book.id)
        serializer = BookSerializer(queryset, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(res.data, serializer.data)

    def test_unauth_book_cannot_create(self):
        res = self.client.post(BOOK_URL, book_defaults)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauth_book_cannot_delete(self):
        book = sample_book()
        url = reverse("books:book-detail", args=[book.id])
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBookTestVew(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test1@test1.com",
            password="TestUser1",
        )
        self.client.force_authenticate(self.user)

    def test_auth_book_cannot_create(self):
        res = self.client.post(BOOK_URL, book_defaults)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_auth_book_cannot_delete(self):
        book = sample_book()
        url = reverse("books:book-detail", args=[book.id])
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBookTestVew(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test1@test1.com",
            password="TestUser1",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_admin_book_create(self):
        res = self.client.post(BOOK_URL, book_defaults)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_book_delete(self):
        book = sample_book()
        url = reverse("books:book-detail", args=[book.id])
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
