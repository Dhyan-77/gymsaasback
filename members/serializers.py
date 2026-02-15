from rest_framework import serializers
from .models import Member


class MemberSerializer(serializers.ModelSerializer):
    days_left = serializers.ReadOnlyField()

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
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "days_left", "created_at")


    def validate(self, attrs):
       
        start = attrs.get("start_date")
        end = attrs.get("end_date")

       
        if self.instance:
            if start is None:
                start = self.instance.start_date
            if end is None:
                end = self.instance.end_date

        if start and end and end <= start:
            raise serializers.ValidationError("end_date must be after start_date.")

        return attrs
