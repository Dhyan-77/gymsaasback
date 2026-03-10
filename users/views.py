from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny,IsAuthenticated
from billing.models import OwnerSubscription
from django.utils import timezone
from .serializers import signupserializers


class SignupView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request):
        serializer = signupserializers(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "message": "Signup successful",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                },
            },
            status=status.HTTP_201_CREATED,
        )





class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
        })








class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sub = (
            OwnerSubscription.objects
            .filter(owner=request.user)
            .order_by("-created_at")
            .first()
        )

        if not sub:
            return Response({
                "status": "none",
                "is_active": False,
                "current_end": None,
                "days_remaining": 0,
                "message": "No subscription found.",
            })

        now = timezone.now()
        days_remaining = 0

        if sub.current_end:
            delta = sub.current_end - now
            days_remaining = max(delta.days, 0)

        has_access = False
        message = "Subscription inactive. Please subscribe to continue."

        if sub.status == OwnerSubscription.Status.ACTIVE:
            has_access = True
            message = "Subscription is active."

        elif (
            sub.status == OwnerSubscription.Status.CANCELLED
            and sub.current_end
            and sub.current_end > now
        ):
            has_access = True
            message = f"Auto-renew cancelled. Access is active until {sub.current_end}."

        elif (
            sub.status in [OwnerSubscription.Status.HALTED, OwnerSubscription.Status.PAUSED]
            and sub.current_end
            and sub.current_end > now
        ):
            has_access = True
            message = f"Subscription is paused/ halted, but access remains active until {sub.current_end}."

        return Response({
            "status": sub.status,
            "is_active": has_access,
            "current_end": sub.current_end,
            "days_remaining": days_remaining,
            "message": message,
        })