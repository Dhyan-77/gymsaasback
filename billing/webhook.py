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
    authentication_classes = []  # Razorpay is not logged in
    permission_classes = [AllowAny]

    def post(self, request):
        # 1) Raw body + signature header
        body_bytes = request.body  # bytes (RAW)
        body_str = body_bytes.decode("utf-8")  # ✅ verify_webhook_signature expects str

        signature = (
            request.headers.get("X-Razorpay-Signature")
            or request.META.get("HTTP_X_RAZORPAY_SIGNATURE")
            or ""
        )

        if not signature:
            # No signature => not Razorpay (or proxy stripped header)
            return HttpResponse("Missing signature", status=400)

        # 2) Verify signature
        try:
            razorpay_client.utility.verify_webhook_signature(
                body_str,
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET,
            )
        except Exception as e:
            # Important: return 400 so Razorpay knows it failed (and retries)
            return HttpResponse(f"Invalid signature: {str(e)}", status=400)

        # 3) Parse payload
        try:
            payload = json.loads(body_str)
        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)

        event = payload.get("event", "unknown")

        # 4) Extract subscription id (some events may not contain it)
        subscription_entity = (
            payload.get("payload", {})
            .get("subscription", {})
            .get("entity", {})
        )
        subscription_id = subscription_entity.get("id")

        # If event doesn't include subscription info, acknowledge (200) and exit.
        if not subscription_id:
            # Still optionally store event for audit:
            PaymentEvent.objects.create(
                subscription=None,
                event_type=event,
                razorpay_payment_id=None,
                razorpay_invoice_id=None,
                amount_inr=None,
                payload=payload,
            )
            return HttpResponse(status=200)

        sub = OwnerSubscription.objects.filter(
            razorpay_subscription_id=subscription_id
        ).first()

        # If we can't match, ACK 200 so Razorpay doesn't retry forever.
        if not sub:
            PaymentEvent.objects.create(
                subscription=None,
                event_type=event,
                razorpay_payment_id=None,
                razorpay_invoice_id=None,
                amount_inr=None,
                payload=payload,
            )
            return HttpResponse(status=200)

        # 5) Log event (audit/debug)
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

        # 6) Update subscription status + dates (idempotent)
        try:
            if event in ("subscription.activated", "subscription.charged", "subscription.resumed"):
                sub.status = OwnerSubscription.Status.ACTIVE

                # Fetch subscription from Razorpay to get dates
                rp = razorpay_client.subscription.fetch(subscription_id)
                sub.current_start = _ts_to_dt(rp.get("current_start"))
                sub.current_end = _ts_to_dt(rp.get("current_end"))

                # customer_id may exist on rp data (optional)
                rp_customer_id = rp.get("customer_id")
                if rp_customer_id and not sub.razorpay_customer_id:
                    sub.razorpay_customer_id = rp_customer_id
                    sub.save(update_fields=["status", "current_start", "current_end", "razorpay_customer_id"])
                else:
                    sub.save(update_fields=["status", "current_start", "current_end"])

            elif event in ("subscription.halted", "subscription.paused"):
                sub.status = OwnerSubscription.Status.HALTED
                sub.save(update_fields=["status"])

            elif event == "subscription.cancelled":
                sub.status = OwnerSubscription.Status.CANCELLED
                sub.save(update_fields=["status"])

            elif event == "subscription.completed":
                sub.status = OwnerSubscription.Status.EXPIRED
                sub.save(update_fields=["status"])

        except Exception:
            # Even if update fails, ACK 200 to prevent endless retries.
            # The PaymentEvent is already stored, so you can replay/fix later.
            return HttpResponse(status=200)

        return HttpResponse(status=200)