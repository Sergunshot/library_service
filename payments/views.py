from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from payments.models import Payment
from payments.serializers import (
    PaymentSerializer,
    PaymentDetailSerializer,
)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("borrowing")
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user

        if not self.request.user.is_staff:
            return self.queryset.filter(borrowing__user=user)

        return self.queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PaymentDetailSerializer

        return PaymentSerializer
