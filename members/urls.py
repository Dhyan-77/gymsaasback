from django.urls import path
from .views import GymMemberListCreateView,ExpiringMembersView,GymMemberDetailView,GymMemberDeleteView


urlpatterns = [
    path("gyms/<uuid:gym_id>/members/", GymMemberListCreateView.as_view(), name="gym-members-list-create"),
     path(
        "gyms/<uuid:gym_id>/members/expiring/",ExpiringMembersView.as_view(),name="expiring-members",
    ),

     path("gyms/<uuid:gym_id>/members/<int:member_id>/", GymMemberDetailView.as_view(), name="gym-member-detail"),
    path("gyms/<uuid:gym_id>/members/<int:member_id>/delete",GymMemberDeleteView.as_view(), name="gym-member-delete"),
]

