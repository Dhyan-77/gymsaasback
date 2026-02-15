from rest_framework.generics import ListCreateAPIView,ListAPIView,RetrieveUpdateAPIView,RetrieveDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from datetime import timedelta
from django.utils import timezone
from .models import Member
from .serializers import MemberSerializer
from gym.models import Gym
from rest_framework.filters import SearchFilter, OrderingFilter


class GymMemberListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    serializer_class = MemberSerializer
    lookup_url_kwarg = "member_id"  

    def get_gym(self):
        gym_id = self.kwargs["gym_id"]
        user = self.request.user

        gym = Gym.objects.filter(id=gym_id, owner=user).first()
        if not gym:
            raise NotFound("Gym not found.")
        return gym

  