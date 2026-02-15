from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import SaaSPlan, OwnerSubscription
from .client import razorpay_client


class CreateSubscriptionCheckout(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")

      
        plan = get_object_or_404(SaaSPlan, id=plan_id, is_active=True)

    
        sub, _ = OwnerSubscription.objects.get_or_create(
            owner=request.user,
            defaults={"plan": plan}
        )

        sub.plan = plan
        sub.status = OwnerSubscription.Status.CREATED
        sub.save(update_fields=["plan", "status"])

       
        total_count = 120 if plan.interval == "monthly" else 10

        razorpay_sub = razorpay_client.subscription.create({
            "plan_id": plan.razorpay_plan_id,
            "total_count": total_count,
            "quantity": 1,
            "customer_notify": 1,
            "notes": {
                "owner_id": str(request.user.id),
                "plan_id": str(plan.id),
            }
        })

        
        sub.razorpay_subscription_id = razorpay_sub["id"]
        sub.save(update_fields=["razorpay_subscription_id"])

       
        return Response({
            "razorpay_key": razorpay_client.auth[0],  
            "subscription_id": razorpay_sub["id"],
            "status": razorpay_sub.get("status"),
        })

