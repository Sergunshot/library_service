from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import ForeignKey
from books.models import Book

FINE_MULTIPLIER = 2


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="borrowings")

    class Meta:
        ordering = ("borrow_date",)

    @property
    def is_active(self) -> bool:
        return not bool(self.actual_return_date)

    def __str__(self):
        return f"id: {self.id} | book: {self.book} borrowed: {str(self.borrow_date)} by: {self.user}"

    @staticmethod
    def book_borrowing(book) -> None:
        book.inventory -= 1
        book.save()

    @staticmethod
    def validate_borrowing(inventory, error_to_raise) -> None:
        if inventory == 0:
            raise error_to_raise(
                {"book": "You can't borrowing this book, its inventory is zero."}
            )

    def clean(self) -> None:
        Borrowing.validate_borrowing(self.book.inventory, ValueError)

    def save(self, *args, **kwargs) -> None:
        self.clean()
        return super().save(*args, **kwargs)

    def return_book(self) -> None:
        self.book.inventory += 1
        self.book.save()
        self.actual_return_date = datetime.today()
        self.save()

    def get_borrowing_days(self) -> int:
        last_date = self.expected_return_date.date()
        first_date = self.borrow_date.date()

        return (last_date - first_date).days

    def get_price(self) -> Decimal:
        return self.get_borrowing_days() * self.book.daily_fee

    def get_overdue_days(self) -> int:
        actual_return_date = self.actual_return_date.date()
        expected_return_date = self.expected_return_date.date()

        return (actual_return_date - expected_return_date).days

    def get_overdue_price(self) -> Decimal:
        daily_fee = self.book.daily_fee
        fine_multiplier = Decimal(FINE_MULTIPLIER)

        return self.get_overdue_days() * daily_fee * fine_multiplier
