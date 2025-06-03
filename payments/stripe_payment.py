import stripe
from django.urls import reverse
from rest_framework.request import Request

from borrowing.models import Borrowing
from library_service import settings
from payments.models import Payment


stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_session(
    borrowing: Borrowing, request: Request
) -> stripe.checkout.Session:
    price = borrowing.get_price()
    borrowing_days = borrowing.get_borrowing_days()
    success_url = request.build_absolute_uri(
        reverse("payment:payment-success", args=[borrowing.id])
    )
    cancel_url = request.build_absolute_uri(
        reverse("payment:payment-cancel", args=[borrowing.id])
    )

    session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Borrowing book: '{borrowing.book.title}'",
                        "description": f"User '{borrowing.user.email}' "
                        f"borrowing book '{borrowing.book}' "
                        f"for '{borrowing_days}' days.",
                    },
                    "unit_amount": int(price * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
    )

    Payment.objects.update_or_create(
        borrowing=borrowing,
        defaults={
            "session_url": session.url,
            "session_id": session.id,
            "money_to_pay": price,
            "type": Payment.TypeChoices.PAYMENT,
            "status": "Pending",
        },
    )

    return session
