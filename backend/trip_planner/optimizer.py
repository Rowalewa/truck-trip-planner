import requests
import json
from django.conf import settings
from .models import TruckStop
import math

def geocode_location(location_string):
    """
    Attempts to geocode by falling back to Nominatim safely, since the local
    database only contains text-based state and city profiles without coordinates.
    """
    url = f"https://nominatim.openstreetmap.org/search"
    headers = {
        'User-Agent': 'TruckTripPlannerAssessment/1.0',
        'From': 'safety-buffer-compliance@domain.com'
    }
    params = {'q': location_string, 'format': 'json', 'limit': 1}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Geocoding error for {location_string}: {e}")
    return None

def run_trip_simulation(start_str, pickup_str, dropoff_str, cycle_hours_used):
    """
    Executes trip optimization using exactly ONE consolidated external routing call,
    calculating fuel stops using valid database attributes (state and retail_price).
    """
    MAX_RANGE_MILES = 500
    SAFETY_BUFFER_MILES = 450
    MILES_PER_GALLON = 10
    FALLBACK_FUEL_PRICE = 3.50

    # Retrieve coordinate anchors
    start_coords = geocode_location(start_str)
    pickup_coords = geocode_location(pickup_str)
    dropoff_coords = geocode_location(dropoff_str)
    
    if not start_coords or not pickup_coords or not dropoff_coords:
        return {"error": "Could not locate one or more entered addresses."}

    # --- SINGLE CONSOLIDATED EXTERNAL NETWORK CALL ---
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{pickup_coords[1]},{pickup_coords[0]};{dropoff_coords[1]},{dropoff_coords[0]}"
    params = {'overview': 'full', 'geometries': 'geojson'}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if not data or not data.get('routes'):
            return {"error": "Could not calculate driving routes between locations."}
        
        route = data['routes'][0]
        legs = route['legs']
        full_geometry = route['geometry']['coordinates']
        full_path = [[lat, lon] for lon, lat in full_geometry]
        
        # Parse Leg 1 (Start -> Pickup)
        leg_1_dist = legs[0]['distance'] * 0.000621371
        leg_1_dur = legs[0]['duration'] / 3600.0
        
        # Parse Leg 2 (Pickup -> Dropoff)
        leg_2_dist = legs[1]['distance'] * 0.000621371
        leg_2_dur = legs[1]['duration'] / 3600.0

        # Split unified geometry array based on proximity to pickup coordinates
        closest_idx = 0
        min_dist = float('inf')
        for i, (lat, lon) in enumerate(full_path):
            d = (lat - pickup_coords[0])**2 + (lon - pickup_coords[1])**2
            if d < min_dist:
                min_dist = d
                closest_idx = i

        leg_1 = {'distance': leg_1_dist, 'duration': leg_1_dur, 'path': full_path[:closest_idx + 1]}
        leg_2 = {'distance': leg_2_dist, 'duration': leg_2_dur, 'path': full_path[closest_idx:]}

    except Exception as e:
        return {"error": f"External Routing Matrix Connection Failure: {e}"}

    # --- SIMULATION ENGINE ---
    timeline_events = []
    markers = [
        {"name": f"Start: {start_str}", "coords": start_coords, "type": "origin"},
        {"name": f"Pickup: {pickup_str}", "coords": pickup_coords, "type": "pickup"},
        {"name": f"Dropoff: {dropoff_str}", "coords": dropoff_coords, "type": "dropoff"}
    ]
    
    total_minutes = 0
    odometer_since_fuel = 0
    total_fuel_cost = 0.0
    driving_minutes_today = 0
    duty_minutes_today = 0
    elapsed_since_last_break = 0
    
    def log_event(status, duration_mins, description):
        nonlocal total_minutes, driving_minutes_today, duty_minutes_today, elapsed_since_last_break
        start_time = total_minutes
        end_time = total_minutes + duration_mins
        
        timeline_events.append({
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration_mins,
            "description": description
        })
        
        if status == "Driving":
            driving_minutes_today += duration_mins
            duty_minutes_today += duration_mins
            elapsed_since_last_break += duration_mins
        elif status == "On Duty (Not Driving)":
            duty_minutes_today += duration_mins
            elapsed_since_last_break += duration_mins
        elif status in ["Off Duty", "Sleeper Berth"]:
            if duration_mins >= 600:
                driving_minutes_today = 0
                duty_minutes_today = 0
                elapsed_since_last_break = 0
            elif duration_mins >= 30:
                elapsed_since_last_break = 0
                duty_minutes_today += duration_mins 
        total_minutes = end_time

    def simulate_leg(leg_data, target_state, label):
        nonlocal odometer_since_fuel, total_fuel_cost
        remaining_mins = int(leg_data['duration'] * 60)
        speed_mpm = leg_data['distance'] / remaining_mins if remaining_mins > 0 else 0
        
        while remaining_mins > 0:
            if driving_minutes_today >= 660 or duty_minutes_today >= 840:
                log_event("Sleeper Berth", 600, "Mandatory 10-hour rest period (Daily cycle reset)")
                continue
            if elapsed_since_last_break >= 480:
                log_event("Off Duty", 30, "Mandatory 30-minute rest break (8-hour rule)")
                continue

            mins_to_8_hr_break = max(0, 480 - elapsed_since_last_break)
            mins_to_11_hr_break = max(0, 660 - driving_minutes_today)
            mins_to_14_hr_break = max(0, 840 - duty_minutes_today)
            mins_to_fuel_buffer = max(0, (SAFETY_BUFFER_MILES - odometer_since_fuel) / speed_mpm) if speed_mpm > 0 else 9999
            
            drive_chunk = min(remaining_mins, mins_to_8_hr_break, mins_to_11_hr_break, mins_to_14_hr_break, int(mins_to_fuel_buffer))
            
            if drive_chunk > 0:
                log_event("Driving", drive_chunk, f"Driving towards {label}")
                odometer_since_fuel += (drive_chunk * speed_mpm)
                remaining_mins -= drive_chunk
                
                if odometer_since_fuel >= SAFETY_BUFFER_MILES:
                    # Query strictly by valid fields: state and retail_price
                    cheapest_stop = TruckStop.objects.filter(state=target_state).order_by('retail_price').first()
                    fuel_price = float(cheapest_stop.retail_price) if cheapest_stop else FALLBACK_FUEL_PRICE
                    
                    gallons_needed = odometer_since_fuel / MILES_PER_GALLON
                    total_fuel_cost += (gallons_needed * fuel_price)
                    
                    stop_name = cheapest_stop.name if cheapest_stop else "Optimized Fuel Station"
                    log_event("On Duty (Not Driving)", 30, f"Fuel Stop: {stop_name} (${fuel_price:.2f}/gal)")
                    
                    total_leg_mins = max(1, int(leg_data['duration'] * 60))
                    ratio = min(1.0, (total_leg_mins - remaining_mins) / total_leg_mins)
                    idx = int(ratio * (len(leg_data['path']) - 1))
                    fuel_coords = leg_data['path'][idx] if leg_data['path'] else start_coords
                    
                    markers.append({"name": f"Fuel: {stop_name}", "coords": fuel_coords, "type": "fuel"})
                    odometer_since_fuel = 0
            else:
                if odometer_since_fuel >= SAFETY_BUFFER_MILES or int(mins_to_fuel_buffer) <= 0:
                    cheapest_stop = TruckStop.objects.filter(state=target_state).order_by('retail_price').first()
                    fuel_price = float(cheapest_stop.retail_price) if cheapest_stop else FALLBACK_FUEL_PRICE
                    
                    gallons_needed = odometer_since_fuel / MILES_PER_GALLON
                    total_fuel_cost += (gallons_needed * fuel_price)
                    
                    stop_name = cheapest_stop.name if cheapest_stop else "Optimized Fuel Station"
                    log_event("On Duty (Not Driving)", 30, f"Fuel Stop: {stop_name} (${fuel_price:.2f}/gal)")
                    
                    total_leg_mins = max(1, int(leg_data['duration'] * 60))
                    ratio = min(1.0, (total_leg_mins - remaining_mins) / total_leg_mins)
                    idx = int(ratio * (len(leg_data['path']) - 1))
                    fuel_coords = leg_data['path'][idx] if leg_data['path'] else start_coords
                    
                    markers.append({"name": f"Fuel: {stop_name}", "coords": fuel_coords, "type": "fuel"})
                    odometer_since_fuel = 0
                else:
                    log_event("Off Duty", 30, "Mandatory 30-minute rest break (8-hour rule)")

    # Execute Simulation Legs
    state_1 = pickup_str.split(",")[-1].strip().split(" ")[0]
    simulate_leg(leg_1, state_1, "Pickup location")
    
    if driving_minutes_today >= 660 or duty_minutes_today >= 840:
        log_event("Sleeper Berth", 600, "Mandatory 10-hour rest period (Daily cycle reset)")
    log_event("On Duty (Not Driving)", 60, "Loading cargo at Pickup point")
    
    # Execute Leg 2
    state_2 = dropoff_str.split(",")[-1].strip().split(" ")[0]
    simulate_leg(leg_2, state_2, "Dropoff destination")
    
    if driving_minutes_today >= 660 or duty_minutes_today >= 840:
        log_event("Sleeper Berth", 600, "Mandatory 10-hour rest period (Daily cycle reset)")
    log_event("On Duty (Not Driving)", 60, "Unloading cargo at Dropoff point")

    # Group into 24-hour logs
    days_payload = {}
    for event in timeline_events:
        start_day = (event['start_time'] // 1440) + 1
        end_day = (event['end_time'] // 1440) + 1
        current_event_start = event['start_time']
        
        for day in range(start_day, end_day + 1):
            day_start_bound = (day - 1) * 1440
            day_end_bound = day * 1440
            
            chunk_start = max(current_event_start, day_start_bound)
            chunk_end = min(event['end_time'], day_end_bound)
            
            if chunk_start >= chunk_end:
                continue
            if day not in days_payload:
                days_payload[day] = []
                
            days_payload[day].append({
                "status": event['status'],
                "start_minute": chunk_start - day_start_bound,
                "end_minute": chunk_end - day_start_bound,
                "description": event['description']
            })
            current_event_start = chunk_end

    # Clean, safely rounded outputs for the final payload dictionary contract
    return {
        "total_distance_miles": round(leg_1['distance'] + leg_2['distance'], 2),
        "total_duration_hours": round(total_minutes / 60.0, 2),
        "total_fuel_cost": round(total_fuel_cost, 2),
        "route_geometry": leg_1['path'] + leg_2['path'],
        "markers": markers,
        "eld_days": days_payload
    }