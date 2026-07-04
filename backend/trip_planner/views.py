from django.shortcuts import render
from rest_framework.views import APIView # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework import status # type: ignore
from .optimizer import run_trip_simulation

# Create your views here.
def trip_dashboard_view(request):
    """Serves the front-end map and ELD visual cockpit interface."""
    return render(request, 'index.html')
'''Create a class-based API view (APIView) that takes incoming JSON payload data, 
forwards it to our simulation optimizer, and returns the formatted payload as an HTTP response.'''

class PlanTripView(APIView):
    """
    Accepts trip parameters via POST, runs the HOS and fuel optimizations,
    and returns a full spatial and graphical timeline payload.
    """
    def post(self, request, *args, **kwargs):
        data = request.data
        
        # 1. Extract and validate incoming request payload fields
        current_location = data.get("current_location")
        pickup_location = data.get("pickup_location")
        dropoff_location = data.get("dropoff_location")
        cycle_hours_used = data.get("cycle_hours_used", 0)
        
        if not all([current_location, pickup_location, dropoff_location]):
            return Response(
                {"error": "Missing required fields. Please supply current_location, pickup_location, and dropoff_location."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            cycle_hours_used = float(cycle_hours_used)
        except ValueError:
            return Response(
                {"error": "cycle_hours_used must be a numeric value representing hours."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Invoke our Phase 3 calculation engine
        result = run_trip_simulation(
            start_str=current_location,
            pickup_str=pickup_location,
            dropoff_str=dropoff_location,
            cycle_hours_used=cycle_hours_used
        )
        
        # 3. Handle errors thrown by geocoding/routing internal checks
        if "error" in result:
            return Response(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
        # 4. Return the fully computed spatial route and timeline maps
        return Response(result, status=status.HTTP_200_OK)