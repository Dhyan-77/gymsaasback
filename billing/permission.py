from rest_framework.permissions import BasePermission
from django.utils import timezone

from billing.models import OwnerSubscription


class HasActiveSubscription(BasePermission):
    message = "Subscription inactive. Please subscribe to continue."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            print("SUB CHECK: unauthenticated")
            return False

        sub = (
            OwnerSubscription.objects
            .filter(owner=user)
            .order_by("-created_at")
            .first()
        )

        if not sub:
            print(f"SUB CHECK: no subscription for user={user.id}")
            return False

        now = timezone.now()
        print(
            "SUB CHECK:",
            {
                "user_id": user.id,
                "status": sub.status,
                "current_start": sub.current_start,
                "current_end": sub.current_end,
                "now": now,
            }
        )

        if sub.status == OwnerSubscription.Status.ACTIVE:
            if sub.current_start and sub.current_start > now:
                print("SUB CHECK RESULT: False (current_start in future)")
                return False
            if sub.current_end and sub.current_end <= now:
                print("SUB CHECK RESULT: False (expired active subscription)")
                return False
            print("SUB CHECK RESULT: True (active)")
            return True

        if sub.status == OwnerSubscription.Status.CANCELLED:
            if sub.current_end and sub.current_end > now:
                print("SUB CHECK RESULT: True (cancelled but still paid)")
                return True
            print("SUB CHECK RESULT: False (cancelled and expired/no end)")
            return False

        if sub.status in [OwnerSubscription.Status.HALTED, OwnerSubscription.Status.PAUSED]:
            if sub.current_end and sub.current_end > now:
                print("SUB CHECK RESULT: True (halted/paused but still paid)")
                return True
            print("SUB CHECK RESULT: False (halted/paused and expired/no end)")
            return False

        print("SUB CHECK RESULT: False (default)")
        return False