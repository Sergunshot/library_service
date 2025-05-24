from borrowing.borrowing_overdue import check_borrowings_overdue
from celery import shared_task


@shared_task
def check_borrowings() -> None:
    return check_borrowings_overdue()
