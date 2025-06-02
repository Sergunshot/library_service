from datetime import datetime

from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.relations import SlugRelatedField, StringRelatedField

from books.serializers import BookSerializer
from borrowing.models import Borrowing
from payments.models import Payment


class BorrowingSerializer(serializers.ModelSerializer):
    user = SlugRelatedField(read_only=True, slug_field="email")
    book = BookSerializer(read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "book",
            "user",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "is_active"
        )
        read_only_fields = ("is_active", )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Borrowing
        fields = ("id", "book", "user", "borrow_date", "expected_return_date", )

    def validate(self, attrs):
        data = super(BorrowingCreateSerializer, self).validate(attrs)

        user = self.context["request"].user
        pending_payment = Payment.objects.filter(
            borrowing__user=user,
            status__in=(
                Payment.StatusChoices.PENDING,
                Payment.StatusChoices.EXPIRED,
            ),
        ).first()

        if pending_payment:
            raise ValidationError(
                {
                    "You cannot borrow new books until pending/expired payment exist. "
                    "Detail of your the payment:": [
                        f"id: {pending_payment.id}",
                        f"status: {pending_payment.status}",
                        f"type: {pending_payment.type}",
                        f"money to pay: {pending_payment.money_to_pay}",
                        f"session id: {pending_payment.session_id}",
                        f"session url: {pending_payment.session_url}",
                        f"borrowing book: {pending_payment.borrowing.book}",
                    ]
                }
            )

        Borrowing.validate_borrowing(
            attrs["book"].inventory, serializers.ValidationError
        )

        return data

    @atomic
    def create(self, validated_data):
        book = validated_data["book"]
        Borrowing.book_borrowing(book)

        borrowing = Borrowing.objects.create(**validated_data)

        return borrowing


class BorrowingReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id",)

    def validate(self, attrs):
        data = super(BorrowingReturnSerializer, self).validate(attrs)
        borrowing = self.instance
        actual_return_date = borrowing.actual_return_date

        if borrowing.actual_return_date:
            raise serializers.ValidationError(
                {
                    f"Borrowing: {borrowing}": f"The borrowing already returned on {actual_return_date}."
                }
            )

        return data

    @atomic
    def update(self, instance, validated_data):
        instance.return_book()
        return instance
