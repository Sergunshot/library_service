from datetime import datetime

from borrowing.models import Borrowing
from borrowing.telegram_notifications import send_message


def check_borrowings_overdue() -> None | str:
    today = datetime.today().date()
    borrowings_overdue = Borrowing.objects.filter(
        expected_return_date__lte=today,
        actual_return_date__isnull=True,
    )

    if borrowings_overdue:
        for borrowing in borrowings_overdue:
            message = (
                f"Borrowing overdue:\n"
                f"borrowing id: {borrowing.id}\n"
                f"book: {borrowing.book.title}\n"
                f"user: {borrowing.user}\n"
                f"borrow_date: {borrowing.borrow_date}\n"
                f"expected_return_date: {borrowing.expected_return_date}"
            )

            send_message(message)

        message = f"{len(borrowings_overdue)} total borrowings overdue today."
        send_message(message)

    else:
        message = "No borrowings overdue today!"
        send_message(message)

    return message
