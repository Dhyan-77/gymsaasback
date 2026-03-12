from django.urls import path
from .views import (
    GymMemberListCreateView,
    ExpiringMembersView,
    GymMemberDetailView,
    GymMemberDeleteView,
    MemberPaymentListCreateView,
    RevenueSummaryView,
    MemberWhatsappReminderView,
    PaymentReceiptView,
)

urlpatterns = [
    path("gyms/<uuid:gym_id>/members/", GymMemberListCreateView.as_view(), name="gym-members-list-create"),
    path("gyms/<uuid:gym_id>/members/expiring/", ExpiringMembersView.as_view(), name="expiring-members"),
    path("gyms/<uuid:gym_id>/members/<int:member_id>/", GymMemberDetailView.as_view(), name="gym-member-detail"),
    path("gyms/<uuid:gym_id>/members/<int:member_id>/delete", GymMemberDeleteView.as_view(), name="gym-member-delete"),

    path("gyms/<uuid:gym_id>/members/<int:member_id>/payments/", MemberPaymentListCreateView.as_view(), name="member-payments"),
    path("gyms/<uuid:gym_id>/dashboard/revenue-summary/", RevenueSummaryView.as_view(), name="revenue-summary"),
    path("gyms/<uuid:gym_id>/members/<int:member_id>/whatsapp-reminder/", MemberWhatsappReminderView.as_view(), name="member-whatsapp-reminder"),
    path("gyms/<uuid:gym_id>/payments/<int:payment_id>/receipt/", PaymentReceiptView.as_view(), name="payment-receipt"),
]