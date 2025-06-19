from decimal import Decimal

import stripe
from django.urls import reverse
from rest_framework.request import Request

from borrowing.models import Borrowing
from library_service import settings
from payments.models import Payment


stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_session(
    borrowing: Borrowing,
    request: Request,
    payment_type: Payment.Type,
    price: Decimal,
    days: int,
) -> stripe.checkout.Session:
    success_url = request.build_absolute_uri(reverse("payment:payment-success"))
    cancel_url = request.build_absolute_uri(reverse("payment:payment-cancel"))

    session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"{payment_type} fee for book: '{borrowing.book.title}'",
                        "description": f"User '{borrowing.user.email}' "
                        f"book detail '{borrowing.book}' "
                        f"for '{days}' days.",
                    },
                    "unit_amount": int(price * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
    )

    Payment.objects.update_or_create(
        borrowing=borrowing,
        type=payment_type,
        defaults={
            "session_url": session.url,
            "session_id": session.id,
            "money_to_pay": price,
            "status": "Pending",
        },
    )

    return session
