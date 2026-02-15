from django.db import models
from django.utils import timezone
from gym.models import Gym


class Member(models.Model):

    class PlanType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    gym = models.ForeignKey(
        Gym,
        on_delete=models.CASCADE,
        related_name="members"
    )

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=10, blank=True)

    plan = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.MONTHLY,
    )

    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()

    course_taken = models.CharField(max_length=255, blank=True)
    offer_taken = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["gym", "end_date"]),
            models.Index(fields=["gym", "name"]),
        ]
        ordering = ["end_date"]

    def __str__(self):
        return f"{self.name} ({self.gym.name})"

    @property
    def days_left(self):
        return (self.end_date - timezone.localdate()).days
