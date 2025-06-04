import stripe
from django.db.transaction import atomic
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from borrowing.serializers import BorrowingSerializer
from borrowing.telegram_notifications import send_message
from payments.models import Payment
from payments.serializers import (
    PaymentSerializer,
    PaymentDetailSerializer,
)
from payments.stripe_payment import create_stripe_session


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

    @extend_schema(
        description="List of user's payments. Admin have access to all users payments.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Check stripe payment session status. "
                    "If status is ok, then update payment instance "
                    "and send notification message to telegram chat bot.",
    )
    @action(methods=["GET"], url_path="success", detail=False)
    def success(self, request, session_id=None):
        session_id = request.query_params.get("session_id", None)
        if not session_id:
            return Response(
                {"message": "Payment parameter not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payment = get_object_or_404(
            Payment,
            session_id=request.GET.get("session_id"),
            status=Payment.StatusChoices.PENDING,
            type=Payment.TypeChoices.PAYMENT,
        )
        session = stripe.checkout.Session.retrieve(session_id)

        if session.get("payment_status") == "paid":
            data = {
                "status": Payment.StatusChoices.PAID,
                "type": Payment.TypeChoices.PAYMENT,
            }
            serializer = self.get_serializer(payment, data=data)

            if serializer.is_valid():
                serializer.save()

                message = (
                    f"Successful payment:\n"
                    f"${payment.money_to_pay} USD\n"
                    f"Borrowing details:\n"
                    f"book: {payment.borrowing.book} "
                    f"user: {payment.borrowing.user}\n"
                    f"borrow date: {payment.borrowing.borrow_date.date()}\n"
                    f"expected return date: {payment.borrowing.expected_return_date.date()}"
                )
                send_message(message)

                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        description="If user cancel payment during payment session, "
                    "show message about available payment session "
                    "for only 24h.",
    )
    @action(methods=["GET"], url_path="cancel", detail=False)
    def cancel(self, request):
        raise ValidationError(
            "Payment can be paid a bit later, but the session is available for only 24h."
        )

    @extend_schema(
        description="If the payment session is expired user can renew it. "
                    "System update fields in payment instance: session_id, session_url and status.",
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="renew",
    )
    @atomic
    def renew_session(self, request, pk=None):
        user = request.user
        payment = Payment.objects.filter(
            status=Payment.StatusChoices.EXPIRED, borrowing__user=user
        ).first()

        if payment:
            days = payment.borrowing.get_borrowing_days()
            if payment.type == Payment.TypeChoices.FINE:
                days = payment.borrowing.get_overdue_days()

            new_session = create_stripe_session(
                payment.borrowing, request, payment.type, payment.money_to_pay, days
            )

            payment.session_url = new_session.url
            payment.session_id = new_session.id
            payment.status = Payment.StatusChoices.PENDING
            payment.save()

            borrowing_data = BorrowingSerializer(payment.borrowing).data
            return Response(
                {
                    "detail:": "Payment session renewed.",
                    "id": payment.id,
                    "new status": payment.status,
                    "type": payment.type,
                    "money to pay": payment.money_to_pay,
                    "new session id": payment.session_id,
                    "new session url": payment.session_url,
                    "borrowing": borrowing_data,
                }
            )
        return Response(
            {"detail": "There is no expired payment session."},
            status=status.HTTP_404_NOT_FOUND,
        )
