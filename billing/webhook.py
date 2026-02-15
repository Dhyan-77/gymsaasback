import json
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .models import OwnerSubscription, PaymentEvent
from .client import razorpay_client


def _ts_to_dt(ts: int | None):
    """Razorpay timestamps are UNIX seconds."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=dt_timezone.utc)


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    permission_classes = [AllowAny]  # Razorpay is not logged in

    def post(self, request):
        # 1) Raw body + signature header (must be raw)
        body = request.body  # bytes
        signature = request.headers.get("X-Razorpay-Signature", "")

        # 2) Verify signature (security)
        try:
            razorpay_client.utility.verify_webhook_signature(
                body,
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET,
            )
        except Exception:
            return HttpResponse("Invalid signature", status=400)

        payload = json.loads(body.decode("utf-8"))
        event = payload.get("event", "unknown")

        # 3) Extract subscription_id from payload (common structure)
        subscription_entity = (
            payload.get("payload", {})
            .get("subscription", {})
            .get("entity", {})
        )
        subscription_id = subscription_entity.get("id")

        # Some events may not have subscription in payload; ignore safely
        if not subscription_id:
            return HttpResponse(status=200)

        sub = OwnerSubscription.objects.filter(
            razorpay_subscription_id=subscription_id
        ).first()

        # If we can't match, still return 200 so Razorpay doesn't retry forever
        if not sub:
            return HttpResponse(status=200)

        # 4) Log the event (debug/audit)
        payment_entity = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        invoice_entity = (
            payload.get("payload", {})
            .get("invoice", {})
            .get("entity", {})
        )

        PaymentEvent.objects.create(
            subscription=sub,
            event_type=event,
            razorpay_payment_id=payment_entity.get("id"),
            razorpay_invoice_id=invoice_entity.get("id"),
            amount_inr=(payment_entity.get("amount") or 0) // 100 if payment_entity.get("amount") else None,
            payload=payload,
        )

        # 5) Update subscription status + dates
        if event in ("subscription.activated", "subscription.charged", "subscription.resumed"):
            sub.status = OwnerSubscription.Status.ACTIVE

            # Best: fetch subscription from Razorpay to get current_start/current_end
            rp = razorpay_client.subscription.fetch(subscription_id)
            sub.current_start = _ts_to_dt(rp.get("current_start"))
            sub.current_end = _ts_to_dt(rp.get("current_end"))

            sub.save(update_fields=["status", "current_start", "current_end"])

        elif event in ("subscription.halted", "subscription.paused"):
            sub.status = OwnerSubscription.Status.HALTED
            sub.save(update_fields=["status"])

        elif event in ("subscription.cancelled",):
            sub.status = OwnerSubscription.Status.CANCELLED
            sub.save(update_fields=["status"])

        elif event in ("subscription.completed",):
            sub.status = OwnerSubscription.Status.EXPIRED
            sub.save(update_fields=["status"])

        # Always return 200 if handled
        return HttpResponse(status=200)
