from rest_framework import serializers
from rest_framework.relations import SlugRelatedField, StringRelatedField

from borrowing.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    user = SlugRelatedField(read_only=True, slug_field="email")
    book = StringRelatedField()

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
