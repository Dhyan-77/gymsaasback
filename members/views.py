from rest_framework.generics import ListCreateAPIView,ListAPIView,RetrieveUpdateAPIView,RetrieveDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from datetime import timedelta
from django.utils import timezone
from .models import Member
from .serializers import MemberSerializer
from gym.models import Gym
from rest_framework.filters import SearchFilter, OrderingFilter
from billing.permission import HasActiveSubscription
from rest_framework.generics import (
    ListCreateAPIView,
    ListAPIView,
    RetrieveUpdateAPIView,
    RetrieveDestroyAPIView,
    CreateAPIView
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper, Q
from .models import Member, Payment
from .serializers import MemberSerializer, PaymentSerializer, PaymentCreateSerializer


class GymMemberListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = MemberSerializer


    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "phone", "course_taken", "offer_taken"]
    ordering_fields = ["end_date", "name", "created_at"]
    ordering = ["end_date"]

    def get_gym(self):
        gym_id = self.kwargs["gym_id"]
        user = self.request.user

        gym = Gym.objects.filter(id=gym_id, owner=user).first()
        if not gym:
            raise NotFound("Gym not found.")
        return gym

    def get_queryset(self):
        gym = self.get_gym()
        return Member.objects.filter(gym=gym, is_active=True).order_by("end_date")

    def perform_create(self, serializer):
        gym = self.get_gym()
        serializer.save(gym=gym)






class ExpiringMembersView(ListAPIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = MemberSerializer

    def get_gym(self):
        gym_id = self.kwargs["gym_id"]
        user = self.request.user

        gym = Gym.objects.filter(id=gym_id, owner=user).first()
        if not gym:
            raise NotFound("Gym not found.")
        return gym
    


    def get_queryset(self):
        gym = self.get_gym()


        days = int(self.request.query_params.get("days", 7))



        today = timezone.localdate()
        expiry_limit = today + timedelta(days=days)
        

        
        return Member.objects.filter(
            gym=gym,
            is_active=True,
            end_date__gte=today,
            end_date__lte=expiry_limit,
        ).order_by("end_date")





class GymMemberDetailView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = MemberSerializer
    lookup_url_kwarg = "member_id"  

    def get_gym(self):
        gym_id = self.kwargs["gym_id"]
        user = self.request.user

        gym = Gym.objects.filter(id=gym_id, owner=user).first()
        if not gym:
            raise NotFound("Gym not found.")
        return gym

    def get_queryset(self):
        gym = self.get_gym()
        return Member.objects.filter(gym=gym)



class GymMemberDeleteView(RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = MemberSerializer
    lookup_url_kwarg = "member_id"

    def get_gym(self):
        gym_id = self.kwargs["gym_id"]
        user = self.request.user

        gym = Gym.objects.filter(id=gym_id, owner=user).first()
        if not gym:
            raise NotFound("Gym not found.")
        return gym

    def get_queryset(self):
        gym = self.get_gym()
        return Member.objects.filter(gym=gym)




class MemberPaymentListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def get_gym(self):
        gym_id = self.kwargs["gym_id"]
        user = self.request.user

        gym = Gym.objects.filter(id=gym_id, owner=user).first()
        if not gym:
            raise NotFound("Gym not found.")
        return gym

    def get_member(self):
        gym = self.get_gym()
        member_id = self.kwargs["member_id"]

        member = Member.objects.filter(gym=gym, id=member_id, is_active=True).first()
        if not member:
            raise NotFound("Member not found.")
        return member

    def get_queryset(self):
        member = self.get_member()
        return Payment.objects.filter(member=member, gym=member.gym).order_by("-payment_date", "-id")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["member"] = self.get_member()
        return context
    


class RevenueSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def get_gym(self):
        gym_id = self.kwargs["gym_id"]
        user = self.request.user

        gym = Gym.objects.filter(id=gym_id, owner=user).first()
        if not gym:
            raise NotFound("Gym not found.")
        return gym

    def get(self, request, *args, **kwargs):
        gym = self.get_gym()
        members = Member.objects.filter(gym=gym, is_active=True)

        totals = members.aggregate(
            total_expected=Sum("total_fee"),
            total_collected=Sum("amount_paid"),
            total_students=Count("id"),
        )

        pending_expr = ExpressionWrapper(
            F("total_fee") - F("amount_paid"),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )

        total_pending = members.aggregate(
            total_pending=Sum(pending_expr)
        )["total_pending"] or 0

        pending_students = members.filter(
            Q(payment_status=Member.PaymentStatus.PENDING) |
            Q(payment_status=Member.PaymentStatus.PARTIAL)
        ).count()

        return Response({
            "total_expected_revenue": totals["total_expected"] or 0,
            "total_collected": totals["total_collected"] or 0,
            "total_pending": total_pending,
            "total_students": totals["total_students"] or 0,
            "pending_students": pending_students,
        })






from urllib.parse import quote


class MemberWhatsappReminderView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def get_gym(self):
        gym_id = self.kwargs["gym_id"]
        user = self.request.user

        gym = Gym.objects.filter(id=gym_id, owner=user).first()
        if not gym:
            raise NotFound("Gym not found.")
        return gym

    def get_member(self):
        gym = self.get_gym()
        member_id = self.kwargs["member_id"]

        member = Member.objects.filter(gym=gym, id=member_id, is_active=True).first()
        if not member:
            raise NotFound("Member not found.")
        return member

    def get(self, request, *args, **kwargs):
        member = self.get_member()

        if not member.phone:
            raise ValidationError("Member does not have a phone number.")

        raw_phone = member.phone.strip()
        phone = f"91{raw_phone}" if len(raw_phone) == 10 else raw_phone

        message = (
            f"Hello {member.name}, your fee payment is pending.\n"
            f"Total Fee: ₹{member.total_fee}\n"
            f"Paid: ₹{member.amount_paid}\n"
            f"Remaining: ₹{member.remaining_fee}\n"
            f"Please clear the balance. Thank you."
        )

        whatsapp_link = f"https://wa.me/{phone}?text={quote(message)}"

        return Response({
            "message": message,
            "whatsapp_link": whatsapp_link,
            "remaining_fee": member.remaining_fee,
            "payment_status": member.payment_status,
        })
    






class PaymentReceiptView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def get_gym(self):
        gym_id = self.kwargs["gym_id"]
        user = self.request.user

        gym = Gym.objects.filter(id=gym_id, owner=user).first()
        if not gym:
            raise NotFound("Gym not found.")
        return gym

    def get_payment(self):
        gym = self.get_gym()
        payment_id = self.kwargs["payment_id"]

        payment = Payment.objects.filter(gym=gym, id=payment_id).select_related("member", "gym").first()
        if not payment:
            raise NotFound("Payment not found.")
        return payment

    def get(self, request, *args, **kwargs):
        payment = self.get_payment()
        member = payment.member

        return Response({
            "receipt_number": payment.receipt_number,
            "business_name": payment.gym.name,
            "student_name": member.name,
            "phone": member.phone,
            "payment_date": payment.payment_date,
            "total_fee": member.total_fee,
            "paid_this_time": payment.amount,
            "total_paid": member.amount_paid,
            "remaining_balance": member.remaining_fee,
            "note": payment.note,
        })    


  