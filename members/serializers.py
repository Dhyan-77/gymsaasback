from rest_framework import serializers
from .models import Member, Payment

from django.db import transaction
from django.utils import timezone

class MemberSerializer(serializers.ModelSerializer):
    days_left = serializers.ReadOnlyField()
    remaining_fee = serializers.ReadOnlyField()

    class Meta:
        model = Member
        fields = (
            "id",
            "name",
            "phone",
            "plan",
            "start_date",
            "end_date",
            "days_left",
            "course_taken",
            "offer_taken",
            "total_fee",
            "amount_paid",
            "remaining_fee",
            "payment_status",
            "last_payment_date",
            "is_active",
            "created_at",
        )
        read_only_fields = (
            "id",
            "days_left",
            "remaining_fee",
            "payment_status",
            "last_payment_date",
            "created_at",
        )

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        total_fee = attrs.get("total_fee")
        amount_paid = attrs.get("amount_paid")

        if self.instance:
            if start is None:
                start = self.instance.start_date
            if end is None:
                end = self.instance.end_date
            if total_fee is None:
                total_fee = self.instance.total_fee
            if amount_paid is None:
                amount_paid = self.instance.amount_paid

        if start and end and end <= start:
            raise serializers.ValidationError("end_date must be after start_date.")

        if total_fee is not None and total_fee < 0:
            raise serializers.ValidationError("total_fee cannot be negative.")

        if amount_paid is not None and amount_paid < 0:
            raise serializers.ValidationError("amount_paid cannot be negative.")

        if total_fee is not None and amount_paid is not None and amount_paid > total_fee:
            raise serializers.ValidationError("amount_paid cannot be greater than total_fee.")

        return attrs

    def create(self, validated_data):
        member = super().create(validated_data)
        member.update_payment_status()
        member.save(update_fields=["payment_status"])
        return member

    def update(self, instance, validated_data):
        member = super().update(instance, validated_data)
        member.update_payment_status()
        member.save(update_fields=["payment_status", "updated_at"])
        return member
    





class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="member.name", read_only=True)
    remaining_after_payment = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "member",
            "student_name",
            "amount",
            "payment_date",
            "note",
            "receipt_number",
            "remaining_after_payment",
            "created_at",
        )
        read_only_fields = (
            "id",
            "receipt_number",
            "student_name",
            "remaining_after_payment",
            "created_at",
        )

    def get_remaining_after_payment(self, obj):
        return obj.member.remaining_fee


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "amount", "payment_date", "note")
        read_only_fields = ("id",)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0.")
        return value

    def validate(self, attrs):
        member = self.context["member"]
        amount = attrs["amount"]

        if member.amount_paid + amount > member.total_fee:
            raise serializers.ValidationError("Payment exceeds total fee.")

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        member = self.context["member"]

        receipt_number = f"RCPT-{member.gym.id.hex[:6].upper()}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        payment = Payment.objects.create(
            member=member,
            gym=member.gym,
            receipt_number=receipt_number,
            **validated_data
        )

        member.amount_paid += payment.amount
        member.last_payment_date = payment.payment_date
        member.update_payment_status()
        member.save(update_fields=["amount_paid", "last_payment_date", "payment_status", "updated_at"])

        return payment

