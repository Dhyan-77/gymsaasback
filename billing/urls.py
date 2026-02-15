from django.urls import path
from .views import CreateSubscriptionCheckout
from .webhook import RazorpayWebhookView

urlpatterns = [
    path("checkout/", CreateSubscriptionCheckout.as_view()),
    path("webhook/razorpay/", RazorpayWebhookView.as_view(), name="razorpay-webhook"),

]
