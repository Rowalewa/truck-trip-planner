import os
import requests
import math
import time
from dotenv import load_dotenv
from .models import TruckStop

# Load environment variables (makes OSENV read your .env file)
load_dotenv()

EARTH_RADIUS_MILES = 3958.8

# Simulation constants
FUEL_INTERVAL_MILES = 1000  # "at least once every 1,000 miles" per assignment
MILES_PER_GALLON = 10
CYCLE_LIMIT_MINUTES = 70 * 60
RESTART_MINUTES = 34 * 60
DAILY_DRIVING_LIMIT_MIN = 11 * 60
DUTY_WINDOW_LIMIT_MIN = 14 * 60
BREAK_REQUIRED_AFTER_MIN = 8 * 60
DAILY_RESET_MIN = 10 * 60


def _haversine_miles(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(min(1, math.sqrt(a)))


def geocode_location(location_string):
    """
    Resolves 'lat,lon' directly with zero API calls, or geocodes a free-text
    address using the stable OpenRouteService Pelias geocoding API.
    """
    if not location_string:
        return None

    query_string = location_string.strip()

    # Fast path: "lat,lon" needs no network call at all[cite: 3]
    parts = query_string.split(",")
    if len(parts) == 2:
        try:
            lat, lon = float(parts[0].strip()), float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except ValueError:
            pass

    # Use ORS for Geocoding
    url = "https://api.openrouteservice.org/geocode/search"
    api_key = os.getenv("ORS_API_KEY")
    
    if not api_key:
        print("Geocoding failed: ORS_API_KEY environment variable is not set.")
        return None

    params = {
        "api_key": api_key,
        "text": query_string,
        "size": 1,
        "boundary.country": "USA" # Limits lookups strictly to the US per assignment requirements
    }

    try:
        response = requests.get(url, params=params, timeout=8)
        if response.status_code == 200:
            data = response.json()
            if data and data.get("features"):
                # Pelias returns coordinates as [longitude, latitude]
                lon, lat = data["features"][0]["geometry"]["coordinates"]
                return float(lat), float(lon)
    except requests.exceptions.RequestException as e:
        print(f"ORS Geocoding error for '{location_string}': {e}")

    return None

def find_cheapest_nearby_station(lat, lon, radius_miles=25, fallback_price=3.50):
    """
    Real geographic fuel search: bounding-box prefilter in the DB, then exact
    haversine distance check, cheapest-first. Expands radius once if nothing
    found close by, and falls back to a flat price only as a last resort.
    """
    for r in (radius_miles, radius_miles * 3):
        margin_deg = r / 55.0
        candidates = TruckStop.objects.filter(
            latitude__isnull=False, longitude__isnull=False,
            latitude__gte=lat - margin_deg, latitude__lte=lat + margin_deg,
            longitude__gte=lon - margin_deg, longitude__lte=lon + margin_deg,
        ).order_by("retail_price")[:200]  # price-sorted cap keeps this cheap

        best = None
        best_price = None
        for stop in candidates:
            dist = _haversine_miles(lat, lon, stop.latitude, stop.longitude)
            if dist <= r and (best_price is None or stop.retail_price < best_price):
                best, best_price = stop, stop.retail_price
        if best is not None:
            return best, float(best.retail_price)

    return None, fallback_price


def _fetch_route(start_coords, pickup_coords, dropoff_coords):
    """
    Fetches the full optimized path using OpenRouteService Directions API.
    Uses POST format to guarantee payload reliability and avoid URL length constraints.
    """
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    
    api_key = os.getenv("ORS_API_KEY")
    if not api_key:
        return None, "System configuration error: ORS API Key is missing from .env"

    # ORS requires coordinates to be ordered as [Longitude, Latitude]
    body = {
        "coordinates": [
            [start_coords[1], start_coords[0]],
            [pickup_coords[1], pickup_coords[0]],
            [dropoff_coords[1], dropoff_coords[0]]
        ],
        # -1 removes the 350m snapping limitation for all 3 waypoints
        "radiuses": [-1, -1, -1], 
        "instructions": True, # so ors populates the segments array with distance/duration
        "preference": "fastest"
    }
    
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json; charset=utf-8"
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=15)
        if response.status_code != 200:
            return None, f"Routing API error: {response.json().get('error', {}).get('message', 'Unknown failure')}"
            
        data = response.json()
        if not data.get("features"):
            return None, "Could not calculate driving routes between locations."
            
        # Return the feature object containing geometry and summary properties
        return data["features"][0], None
    except requests.exceptions.RequestException as e:
        return None, f"External routing service connection failure: {e}"
    
def _build_route_legs(route, pickup_coords):
    """
    Splits the continuous ORS coordinate array into two distinct legs 
    (Start -> Pickup) and (Pickup -> Dropoff) based on spatial proximity.
    """
    # Extract feature data securely
    feature = route["features"][0] if "features" in route else route
    properties = feature.get("properties", {})
    geometry = feature.get("geometry", {})

    segments = properties.get("segments")
    full_geometry = geometry.get("coordinates")

    if not segments or not full_geometry:
        raise KeyError("The routing API response is missing critical segment or path tracking metadata.")

    # Invert [lon, lat] from ORS back to your internal [lat, lon] mapping
    full_path = [[lat, lon] for lon, lat in full_geometry]
    
    # Locate the closest coordinate point matching your pickup waypoint
    closest_idx = min(
        range(len(full_path)),
        key=lambda i: (full_path[i][0] - pickup_coords[0]) ** 2 + (full_path[i][1] - pickup_coords[1]) ** 2,
    )
    
    # ORS reports distance in meters -> convert to miles
    leg_1 = {
        "distance": segments[0]["distance"] * 0.000621371,
        "duration": segments[0]["duration"] / 3600.0,
        "path": full_path[: closest_idx + 1],
    }
    
    leg_2 = {
        "distance": segments[1]["distance"] * 0.000621371,
        "duration": segments[1]["duration"] / 3600.0,
        "path": full_path[closest_idx:],
    }
    
    return leg_1, leg_2
def _initialize_simulation_state(start_str, pickup_str, dropoff_str, start_coords, pickup_coords, dropoff_coords, cycle_hours_used):
    return {
        "timeline_events": [],
        "markers": [
            {"name": f"Start: {start_str}", "coords": start_coords, "type": "origin"},
            {"name": f"Pickup: {pickup_str}", "coords": pickup_coords, "type": "pickup"},
            {"name": f"Dropoff: {dropoff_str}", "coords": dropoff_coords, "type": "dropoff"},
        ],
        "total_minutes": 0,
        "odometer_since_fuel": 0.0,
        "total_fuel_cost": 0.0,
        "driving_minutes_today": 0,
        "duty_minutes_today": 0,
        "elapsed_since_last_break": 0,
        "cycle_minutes_used": cycle_hours_used * 60,
    }


def _log_event(state, status, duration_mins, description):
    start_time = state["total_minutes"]
    end_time = start_time + duration_mins

    state["timeline_events"].append({
        "status": status,
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration_mins,
        "description": description,
    })

    if status == "Driving":
        state["driving_minutes_today"] += duration_mins
        state["duty_minutes_today"] += duration_mins
        state["elapsed_since_last_break"] += duration_mins
        state["cycle_minutes_used"] += duration_mins
    elif status == "On Duty (Not Driving)":
        state["duty_minutes_today"] += duration_mins
        state["elapsed_since_last_break"] += duration_mins
        state["cycle_minutes_used"] += duration_mins
    elif status in ["Off Duty", "Sleeper Berth"]:
        if duration_mins >= RESTART_MINUTES:
            state["driving_minutes_today"] = 0
            state["duty_minutes_today"] = 0
            state["elapsed_since_last_break"] = 0
            state["cycle_minutes_used"] = 0
        elif duration_mins >= DAILY_RESET_MIN:
            state["driving_minutes_today"] = 0
            state["duty_minutes_today"] = 0
            state["elapsed_since_last_break"] = 0
        elif duration_mins >= 30:
            state["elapsed_since_last_break"] = 0

    state["total_minutes"] = end_time


def _simulate_leg(state, leg_data, label, start_coords):
    remaining_mins = int(leg_data["duration"] * 60)
    speed_mpm = leg_data["distance"] / remaining_mins if remaining_mins > 0 else 0
    total_leg_mins = max(1, int(leg_data["duration"] * 60))

    while remaining_mins > 0:
        if state["cycle_minutes_used"] >= CYCLE_LIMIT_MINUTES:
            _log_event(state, "Off Duty", RESTART_MINUTES, "Mandatory 34-hour restart (70-hour/8-day cycle limit reached)")
            continue
        if state["driving_minutes_today"] >= DAILY_DRIVING_LIMIT_MIN or state["duty_minutes_today"] >= DUTY_WINDOW_LIMIT_MIN:
            _log_event(state, "Sleeper Berth", DAILY_RESET_MIN, "Mandatory 10-hour rest period (daily limit reached)")
            continue
        if state["elapsed_since_last_break"] >= BREAK_REQUIRED_AFTER_MIN:
            _log_event(state, "Off Duty", 30, "Mandatory 30-minute rest break (8-hour rule)")
            continue

        mins_to_cycle_limit = max(0, CYCLE_LIMIT_MINUTES - state["cycle_minutes_used"])
        mins_to_8_hr_break = max(0, BREAK_REQUIRED_AFTER_MIN - state["elapsed_since_last_break"])
        mins_to_11_hr_break = max(0, DAILY_DRIVING_LIMIT_MIN - state["driving_minutes_today"])
        mins_to_14_hr_break = max(0, DUTY_WINDOW_LIMIT_MIN - state["duty_minutes_today"])
        mins_to_fuel = max(0, (FUEL_INTERVAL_MILES - state["odometer_since_fuel"]) / speed_mpm) if speed_mpm > 0 else 9999

        drive_chunk = min(
            remaining_mins,
            mins_to_cycle_limit,
            mins_to_8_hr_break,
            mins_to_11_hr_break,
            mins_to_14_hr_break,
            int(mins_to_fuel),
        )

        if drive_chunk > 0:
            _log_event(state, "Driving", drive_chunk, f"Driving towards {label}")
            state["odometer_since_fuel"] += drive_chunk * speed_mpm
            remaining_mins -= drive_chunk

        if state["odometer_since_fuel"] >= FUEL_INTERVAL_MILES or (drive_chunk == 0 and int(mins_to_fuel) <= 0):
            ratio = min(1.0, (total_leg_mins - remaining_mins) / total_leg_mins)
            idx = int(ratio * (len(leg_data["path"]) - 1))
            fuel_coords = leg_data["path"][idx] if leg_data["path"] else start_coords

            cheapest_stop, fuel_price = find_cheapest_nearby_station(fuel_coords[0], fuel_coords[1])
            gallons_needed = state["odometer_since_fuel"] / MILES_PER_GALLON
            state["total_fuel_cost"] += gallons_needed * fuel_price
            stop_name = cheapest_stop.name if cheapest_stop else "Nearest available fuel station"

            _log_event(state, "On Duty (Not Driving)", 30, f"Fuel Stop: {stop_name} (${fuel_price:.2f}/gal)")
            state["markers"].append({"name": f"Fuel: {stop_name}", "coords": fuel_coords, "type": "fuel"})
            state["odometer_since_fuel"] = 0
        elif drive_chunk == 0:
            _log_event(state, "Off Duty", 30, "Mandatory 30-minute rest break (8-hour rule)")


def _apply_post_leg_rest(state):
    if state["cycle_minutes_used"] >= CYCLE_LIMIT_MINUTES:
        _log_event(state, "Off Duty", RESTART_MINUTES, "Mandatory 34-hour restart (70-hour/8-day cycle limit reached)")
    elif state["driving_minutes_today"] >= DAILY_DRIVING_LIMIT_MIN or state["duty_minutes_today"] >= DUTY_WINDOW_LIMIT_MIN:
        _log_event(state, "Sleeper Berth", DAILY_RESET_MIN, "Mandatory 10-hour rest period (daily limit reached)")


def _split_timeline_into_days(timeline_events):
    """
    Slices a continuous timeline into standard 24-hour (1440 minute) ELD log buckets.
    Forces day steps to integer types to safely feed Python's range function[cite: 2].
    """
    days_payload = {}
    for event in timeline_events:
        # Forcing int() ensures that even if times are floats, range() receives integer bounds[cite: 2]
        start_day = int(event["start_time"] // 1440) + 1
        end_day = int(event["end_time"] // 1440) + 1
        current_event_start = event["start_time"]

        for day in range(start_day, end_day + 1):
            day_start_bound = (day - 1) * 1440
            day_end_bound = day * 1440
            
            chunk_start = max(current_event_start, day_start_bound)
            chunk_end = min(event["end_time"], day_end_bound)
            
            if chunk_start >= chunk_end:
                continue
                
            days_payload.setdefault(day, []).append({
                "status": event["status"],
                "start_minute": int(chunk_start - day_start_bound),
                "end_minute": int(chunk_end - day_start_bound),
                "description": event["description"],
            })
            current_event_start = chunk_end
            
    return days_payload
def run_trip_simulation(start_str, pickup_str, dropoff_str, cycle_hours_used):
    """
    Executes trip optimization using exactly ONE consolidated external routing
    call, with a real geographic fuel search and full HOS modeling including
    the 70-hour/8-day cycle (seeded from cycle_hours_used) and 34-hour restart.
    Adverse driving conditions exception is intentionally not modeled.
    """
    start_coords = geocode_location(start_str)
    pickup_coords = geocode_location(pickup_str)
    dropoff_coords = geocode_location(dropoff_str)

    if not start_coords or not pickup_coords or not dropoff_coords:
        return {"error": "Geocoding service timed out or could not resolve one of the entered addresses."}

    route, error = _fetch_route(start_coords, pickup_coords, dropoff_coords)
    if error:
        return {"error": error}

    leg_1, leg_2 = _build_route_legs(route, pickup_coords)
    state = _initialize_simulation_state(start_str, pickup_str, dropoff_str, start_coords, pickup_coords, dropoff_coords, cycle_hours_used)

    _simulate_leg(state, leg_1, "Pickup location", start_coords)
    _apply_post_leg_rest(state)
    _log_event(state, "On Duty (Not Driving)", 60, "Loading cargo at Pickup point")

    _simulate_leg(state, leg_2, "Dropoff destination", start_coords)
    _apply_post_leg_rest(state)
    _log_event(state, "On Duty (Not Driving)", 60, "Unloading cargo at Dropoff point")

    days_payload = _split_timeline_into_days(state["timeline_events"])

    return {
        "total_distance_miles": round(leg_1["distance"] + leg_2["distance"], 2),
        "total_duration_hours": round(state["total_minutes"] / 60.0, 2),
        "total_fuel_cost": round(state["total_fuel_cost"], 2),
        "cycle_hours_used_at_end": round(state["cycle_minutes_used"] / 60.0, 2),
        "route_geometry": leg_1["path"] + leg_2["path"],
        "markers": state["markers"],
        "eld_days": days_payload,
    }
