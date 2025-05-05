from django.db import models
from borrowing.models import Borrowing


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "PENDING"
        PAID = "paid", "PAID"
        EXPIRED = "expired", "EXPIRED"

    class Type(models.TextChoices):
        PAYMENT = "payment", "PAYMENT"
        FINE = "fine", "FINE"

    status = models.CharField(max_length=255, choices=Status.choices, default=Status.PENDING)
    type = models.CharField(max_length=255, choices=Type.choices, default=Type.PAYMENT)
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name="payments")
    session_url = models.URLField(max_length=500, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.type}: {self.status} [ USD {self.money_to_pay} ] {self.borrowing}"