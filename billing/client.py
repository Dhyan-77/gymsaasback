import razorpay
from django.conf import settings

razorpay_client = razorpay.Client(auth=(settings.TEST_API_KEY_ID, settings.TEST_KEY_SECRET))
