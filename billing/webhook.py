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
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=dt_timezone.utc)


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # 1) RAW body + signature
        body_bytes = request.body
        body_str = body_bytes.decode("utf-8", errors="ignore")

        signature = (
            request.headers.get("X-Razorpay-Signature")
            or request.META.get("HTTP_X_RAZORPAY_SIGNATURE")
            or ""
        )
        if not signature:
            return HttpResponse("Missing signature", status=400)

        # 2) Verify signature (must verify on raw string body)
        try:
            razorpay_client.utility.verify_webhook_signature(
                body_str,
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET,
            )
        except Exception:
            return HttpResponse("Invalid signature", status=400)

        # 3) Parse JSON
        try:
            payload = json.loads(body_str)
        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)

        event = payload.get("event", "unknown")

        # 4) Extract subscription id (Razorpay sends different payload shapes for different events)
        subscription_id = (
            payload.get("payload", {})
            .get("subscription", {})
            .get("entity", {})
            .get("id")
        )

        # Some events won't have subscription data; just ACK 200
        if not subscription_id:
            return HttpResponse(status=200)

        sub = OwnerSubscription.objects.filter(
            razorpay_subscription_id=subscription_id
        ).first()

        # If we can't match, ACK 200 (don't retry forever)
        if not sub:
            return HttpResponse(status=200)

        # 5) Log the event (ONLY when sub exists)
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

        amount_paise = payment_entity.get("amount")
        amount_inr = (amount_paise // 100) if isinstance(amount_paise, int) else None

        PaymentEvent.objects.create(
            subscription=sub,
            event_type=event,
            razorpay_payment_id=payment_entity.get("id"),
            razorpay_invoice_id=invoice_entity.get("id"),
            amount_inr=amount_inr,
            payload=payload,
        )

        # 6) Update subscription status + dates
        if event in ("subscription.activated", "subscription.charged", "subscription.resumed"):
            sub.status = OwnerSubscription.Status.ACTIVE

            # Fetch fresh dates from Razorpay (safe)
            try:
                rp = razorpay_client.subscription.fetch(subscription_id)
                sub.current_start = _ts_to_dt(rp.get("current_start"))
                sub.current_end = _ts_to_dt(rp.get("current_end"))

                # Optional: store customer_id if you have the field
                rp_customer_id = rp.get("customer_id")
                if rp_customer_id and hasattr(sub, "razorpay_customer_id") and not sub.razorpay_customer_id:
                    sub.razorpay_customer_id = rp_customer_id

            except Exception:
                # Don’t fail webhook if Razorpay fetch fails
                pass

            sub.save()

        elif event in ("subscription.halted", "subscription.paused"):
            sub.status = OwnerSubscription.Status.HALTED
            sub.save(update_fields=["status"])

        elif event == "subscription.cancelled":
            sub.status = OwnerSubscription.Status.CANCELLED
            sub.save(update_fields=["status"])

        elif event == "subscription.completed":
            sub.status = OwnerSubscription.Status.EXPIRED
            sub.save(update_fields=["status"])

        return HttpResponse(status=200)