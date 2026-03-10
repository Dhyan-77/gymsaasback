from rest_framework.permissions import BasePermission
from django.utils import timezone

from billing.models import OwnerSubscription


class HasActiveSubscription(BasePermission):
    message = "Subscription inactive. Please subscribe to continue."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        sub = (
            OwnerSubscription.objects
            .filter(owner=user)
            .order_by("-created_at")
            .first()
        )

        if not sub:
            return False

        now = timezone.now()

        # Optional model method support
        if hasattr(sub, "is_active_now") and callable(sub.is_active_now):
            return sub.is_active_now()

        # ACTIVE subscription
        if sub.status == OwnerSubscription.Status.ACTIVE:
            if sub.current_start and sub.current_start > now:
                return False
            if sub.current_end and sub.current_end < now:
                return False
            return True

        # CANCELLED but still within paid period
        if (
            sub.status == OwnerSubscription.Status.CANCELLED
            and sub.current_end
            and sub.current_end > now
        ):
            return True

        # HALTED / PAUSED but current paid period still valid
        if (
            sub.status in [OwnerSubscription.Status.HALTED, OwnerSubscription.Status.PAUSED]
            and sub.current_end
            and sub.current_end > now
        ):
            return True

        return False