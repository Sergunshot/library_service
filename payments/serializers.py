from rest_framework import serializers

from borrowing.serializers import BorrowingSerializer
from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="borrowing.user", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "status",
            "type",
            "borrowing",
            "session_url",
            "session_id",
            "money_to_pay",
            "user",
        )


class PaymentDetailSerializer(serializers.ModelSerializer):
    borrowing = BorrowingSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "status",
            "type",
            "borrowing",
            "session_url",
            "session_id",
            "money_to_pay",
        )
