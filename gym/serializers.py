from rest_framework import serializers
from .models import Gym

class GymSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gym
        fields = ("id", "name", "address")
        read_only_fields = ("id",)

