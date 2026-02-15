from rest_framework.generics import ListAPIView,ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import Gym
from .serializers import GymSerializer

class MyGymsListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GymSerializer

    def get_queryset(self):
        return Gym.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)