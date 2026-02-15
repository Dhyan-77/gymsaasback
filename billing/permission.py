from rest_framework.permissions import BasePermission


class HasActiveSubscription(BasePermission):
    message = "Subscription inactive. Please renew to continue."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        sub = getattr(user, "saas_subscription", None)
        if not sub:
            return False

        return sub.is_active_now()
