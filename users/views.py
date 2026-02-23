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
            return Response({"status": "none"})

        days_remaining = None
        if sub.current_end:
            delta = sub.current_end - timezone.now()
            days_remaining = max(delta.days, 0)

        return Response({
            "status": sub.status,
            "current_end": sub.current_end,
            "days_remaining": days_remaining,
        })