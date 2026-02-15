from django.urls import path
from .views import MyGymsListCreateView

urlpatterns = [
    path("", MyGymsListCreateView.as_view(), name="my-gyms-list-create"),
]
