import stripe

from borrowing.borrowing_overdue import check_borrowings_overdue
from celery import shared_task

from library_service import settings
from payments.models import Payment


@shared_task
def check_borrowings() -> None:
    return check_borrowings_overdue()


@shared_task
def check_stripe_session_status():
    pending_payments = Payment.objects.filter(status="PENDING")

    for payment in pending_payments:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(payment.session_id)

        if session["status"] == "expired":
            payment.status = Payment.StatusChoices.EXPIRED
            payment.save()
