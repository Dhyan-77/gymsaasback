from django.conf import settings
from django.db import models
from django.utils import timezone


class SaaSPlan(models.Model):
    class Interval(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    name = models.CharField(max_length=100) 
    interval = models.CharField(max_length=20, choices=Interval.choices)
    amount_inr = models.PositiveIntegerField()  
    is_active = models.BooleanField(default=True)

    
    razorpay_plan_id = models.CharField(max_length=100, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("name", "interval")

    def __str__(self):
        return f"{self.name} {self.interval} ₹{self.amount_inr}"


class OwnerSubscription(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        ACTIVE = "active", "Active"
        HALTED = "halted", "Halted"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saas_subscription"
    )
    plan = models.ForeignKey(SaaSPlan, on_delete=models.PROTECT, related_name="subscriptions")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)


    razorpay_customer_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_subscription_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

   
    current_start = models.DateTimeField(null=True, blank=True)
    current_end = models.DateTimeField(null=True, blank=True)

    cancel_at_period_end = models.BooleanField(default=False)


    trial_end = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active_now(self) -> bool:
        now = timezone.now()
        if self.trial_end and now < self.trial_end:
            return True
        if self.status != self.Status.ACTIVE:
            return False
        if self.current_end and self.current_end < now:
            return False
        return True

    def __str__(self):
        return f"{self.owner.username} -> {self.plan} [{self.status}]"


class PaymentEvent(models.Model):
    subscription = models.ForeignKey(
        OwnerSubscription,
        on_delete=models.CASCADE,
        related_name="events"
    )
    event_type = models.CharField(max_length=100) 
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_invoice_id = models.CharField(max_length=100, null=True, blank=True)
    amount_inr = models.PositiveIntegerField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} - {self.subscription.owner.username}"

