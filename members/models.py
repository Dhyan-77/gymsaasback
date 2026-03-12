from decimal import Decimal
from django.db import models
from django.utils import timezone
from gym.models import Gym


class Member(models.Model):

    class PlanType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PARTIAL = "partial", "Partial"
        PAID = "paid", "Paid"

    gym = models.ForeignKey(
        Gym,
        on_delete=models.CASCADE,
        related_name="members"
    )

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, blank=True)

    plan = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.MONTHLY,
    )

    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()

    course_taken = models.CharField(max_length=255, blank=True)
    offer_taken = models.CharField(max_length=255, blank=True)

    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    last_payment_date = models.DateField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["gym", "end_date"]),
            models.Index(fields=["gym", "name"]),
            models.Index(fields=["gym", "payment_status"]),
        ]
        ordering = ["end_date"]

    def __str__(self):
        return f"{self.name} ({self.gym.name})"

    @property
    def days_left(self):
        return (self.end_date - timezone.localdate()).days

    @property
    def remaining_fee(self):
        remaining = self.total_fee - self.amount_paid
        return remaining if remaining > 0 else Decimal("0.00")

    def update_payment_status(self):
        if self.amount_paid <= 0:
            self.payment_status = self.PaymentStatus.PENDING
        elif self.amount_paid < self.total_fee:
            self.payment_status = self.PaymentStatus.PARTIAL
        else:
            self.payment_status = self.PaymentStatus.PAID


class Payment(models.Model):
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    gym = models.ForeignKey(
        Gym,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=255, blank=True)
    receipt_number = models.CharField(max_length=50, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["gym", "payment_date"]),
            models.Index(fields=["member", "payment_date"]),
        ]
        ordering = ["-payment_date", "-id"]

    def __str__(self):
        return f"{self.member.name} - {self.amount}"