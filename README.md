# 🚚 Autonomous Logistix Dashboard & Trip Planner

A full-stack **truck trip optimization and Hours-of-Service (HOS) compliance engine**. Give it a current location, a pickup, and a drop-off, and it plans the entire legally-compliant trip: driving legs, mandatory FMCSA rest breaks, fuel stops, and the exact daily ELD log sheets a driver would need to file — plus a live map of the whole route.

Built as a Django REST API (the compliance/routing brain) + a React dashboard (map, forms, and hand-drawn 24-hour log charts).

---

## 📊 What It Looks Like

**Route planning + live map**
A single trip is entered once — current location, pickup, drop-off, and hours already used in the driver's cycle — and the dashboard renders the full route with pickup, drop-off, and optimized fuel stop markers.

<img width="1440" height="812" alt="Route planning dashboard" src="https://github.com/user-attachments/assets/128e1622-1811-4c3d-bd97-c265e48e539a" />

**Multi-day HOS log charts**
Long trips get automatically split into calendar-day chunks, each rendered as its own 24-hour log — Off Duty, Sleeper Berth, Driving, On Duty (Not Driving) — with a remarks table showing exactly what happened, where, and for how long.

| Day 1 | Day 2 |
|---|---|
| <img width="700" alt="Day 1 log" src="https://github.com/user-attachments/assets/c63e1559-2522-40fb-8fd8-bc39e2c8d899" /> | <img width="700" alt="Day 2 log" src="https://github.com/user-attachments/assets/bff2e4c5-fbc0-42b2-90c9-8e185d5cd7da" /> |

| Day 3 | Day 4 |
|---|---|
| <img width="700" alt="Day 3 log" src="https://github.com/user-attachments/assets/369eb40c-b66a-4f38-b353-cc72b0658954" /> | <img width="700" alt="Day 4 log" src="https://github.com/user-attachments/assets/06c1a5f3-712c-46e4-83a1-3bedd9ab8653" /> |

---

## 🧠 What This Actually Does

You give it three locations and one number:

| Input | Example |
|---|---|
| Current location | `"Oklahoma City, OK"` or `"35.4676,-97.5164"` |
| Pickup point | `"Tomah, WI"` |
| Drop-off destination | `"Gila Bend, AZ"` |
| Cycle hours already used (of 70) | `35` |

It gives you back:

- **Total distance, total drive time, and estimated fuel cost**
- **A route on the map** with the current location, pickup, drop-off, and every fuel stop marked
- **One daily log per calendar day** the trip spans, each a real 24-hour ELD-style chart with a remarks table (time, status, and what/where — e.g. *"Fuel Stop: KUM & GO #0370 ($2.92/gal), Gretna, NE"*)

Every rule below is actually simulated, not just described:

| Rule | What the engine does |
|---|---|
| 11-hour driving limit | Forces a rest the instant cumulative driving hits 11h in a duty period |
| 14-hour on-duty window | Forces a rest once 14h have elapsed since coming on duty, driving or not |
| 30-minute break every 8 driving hours | Inserted automatically, logged as its own event |
| 10-hour daily reset | Full reset of the daily clocks once triggered |
| 70-hour/8-day cycle | Tracked as a running total seeded by your "cycle hours used" input |
| 34-hour restart | Automatically triggered and zeroes the cycle once the 70-hour ceiling is hit |
| Fuel stops every 1,000 miles | Picks the **cheapest real station within a real geographic radius** of wherever the truck actually is at that point — not just "cheapest in the state" |
| 1-hour pickup / drop-off | Logged as fixed on-duty (not driving) events |

**Adverse driving conditions exception is intentionally not modeled** — this is a deliberate simplification, not an oversight.

---

## 🏗️ How It's Built

```
Browser (React dashboard)
        │  POST /api/plan-trip/
        ▼
Django REST API  ──────────────►  OpenRouteService (routing + geocoding, 1 call/trip)
        │
        ▼
HOS + fuel-cost simulation engine
        │
        ▼
SQLite: ~7,500 real US truck stops, geocoded to lat/lon
```

- **Backend:** Python, Django, Django REST Framework, SQLite
- **Frontend:** React (Vite), Leaflet for the map, hand-drawn SVG for the log charts
- **Routing & geocoding:** [OpenRouteService](https://openrouteservice.org/) — free tier, one consolidated call per trip (multi-waypoint) so it never hammers a rate limit
- **Fuel data:** a real ~8,000-row truck stop price dataset, geocoded once at load time by joining city/state against a static US-cities reference table — so fuel-stop lookups at request time are pure local database queries, not live geocoding calls

---

## 📁 Project Structure

```
truck-trip-planner/
├── backend/
│   ├── config/                      # Django project settings
│   │   ├── settings.py
│   │   └── urls.py                  # routes /api/ → trip_planner.urls
│   ├── trip_planner/                # the actual app
│   │   ├── models.py                # TruckStop (name, city, state, price, lat/lon)
│   │   ├── optimizer.py             # the HOS + routing + fuel-cost engine
│   │   ├── views.py                 # PlanTripView (POST /api/plan-trip/)
│   │   ├── urls.py
│   │   └── management/commands/
│   │       └── seed_fuel.py         # loads + geocodes the fuel price CSV
│   ├── fuel-prices-for-be-assessment.csv   # raw truck stop price data
│   ├── us_cities_ref.csv            # city → lat/lon reference table
│   ├── requirements.txt
│   └── .env.example                 # documents required env vars (not your real secrets)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # dashboard: form, map, EldGrid charts
│   │   └── App.css
│   ├── package.json
│   └── .env.example
│
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites
- **Python 3.9+**
- **Node.js** (18+ recommended)
- A free **OpenRouteService API key** — [sign up here](https://openrouteservice.org/dev/#/signup), it's free and takes about a minute

### 1. Clone the repo

```bash
git clone https://github.com/Rowalewa/truck-trip-planner.git
cd truck-trip-planner
```

### 2. Backend setup

```bash
cd backend
python3 -m venv my_venv
source my_venv/bin/activate        # Windows: my_venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in `backend/` (copy `.env.example` and fill in your real key):

```
SECRET_KEY=your_django_secret_key_here
DEBUG=True
ORS_API_KEY=your_openrouteservice_api_key_here
```

Set up the database and load real fuel station data:

```bash
python manage.py migrate
python manage.py seed_fuel
```

Run it:

```bash
python manage.py runserver
```

The API is now live at **http://127.0.0.1:8000/**.

### 3. Frontend setup

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env      # points VITE_API_URL at your local backend
npm run dev
```

Open the URL Vite prints (typically **http://localhost:5173** or **:5174**).

---

## 🔌 API Reference

### `POST /api/plan-trip/`

**Request body:**

```json
{
  "current_location": "Oklahoma City, OK",
  "pickup_location": "Tomah, WI",
  "dropoff_location": "Gila Bend, AZ",
  "cycle_hours_used": 0
}
```

Each location accepts either a free-text address (geocoded via OpenRouteService) or raw `"lat,lon"` coordinates (skips geocoding entirely for that field).

**Response (abridged):**

```json
{
  "total_distance_miles": 2672.4,
  "total_duration_hours": 78.0,
  "total_fuel_cost": 599.24,
  "cycle_hours_used_at_end": 42.5,
  "route_geometry": [[lat, lon], ...],
  "markers": [
    {"name": "Start: Oklahoma City, OK", "coords": [...], "type": "origin"},
    {"name": "Fuel: KUM & GO #0370", "coords": [...], "type": "fuel"}
  ],
  "eld_days": {
    "1": [
      {"status": "Driving", "start_minute": 0, "end_minute": 480,
       "remark": "Driving towards Pickup location, Wichita, KS"}
    ]
  }
}
```

`eld_days` is keyed by day number, each containing the ordered list of duty events for that calendar day — this is exactly what the frontend's `EldGrid` component renders directly, no server-side image generation involved.

---

## 🎯 Design Decisions Worth Knowing About

- **One routing API call per trip, always.** All three waypoints (current → pickup → drop-off) go into a single OpenRouteService request rather than one call per leg.
- **Fuel-stop search is real geography, not a shortcut.** Stations are bounding-box pre-filtered in the database, then checked against an exact haversine distance from the truck's actual position at that point in the trip — not "cheapest anywhere in the state."
- **The 70-hour/8-day cycle is a running total, not a full rolling ledger.** The only input available is a single "hours used" number, not 8 days of history — so the engine tracks a running total seeded by that number, and only a 34-hour restart zeroes it, which matches how the real regulation's restart provision works.
- **Remarks are real, not placeholders.** Every logged event — driving, breaks, fuel stops, pickup/drop-off — resolves to an actual city/state, either from the fuel station's own data or from a local nearest-city lookup, so nothing in the log ever just says "Unknown."

---

## 🔐 Environment Variables

| Variable | Where | Required | Notes |
|---|---|---|---|
| `ORS_API_KEY` | `backend/.env` | Yes | Free tier at openrouteservice.org |
| `SECRET_KEY` | `backend/.env` | Recommended | Django's secret key; a default is used if omitted, but don't ship that default |
| `DEBUG` | `backend/.env` | No | `True` for local dev, `False` in production |
| `VITE_API_URL` | `frontend/.env` | Yes for deployment | Defaults to `http://127.0.0.1:8000` if unset |

Never commit real `.env` files — only the `.env.example` templates are tracked in git.
