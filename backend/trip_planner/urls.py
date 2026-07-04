from django.urls import path
from .views import PlanTripView # <-- Substitute with your exact API view function/class name

urlpatterns = [
    path('plan-trip/', PlanTripView.as_view(), name='plan_trip_api'), # Maps to /api/plan-trip/
]