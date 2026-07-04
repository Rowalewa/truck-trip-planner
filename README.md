# 🚚 Autonomous Logistix Dashboard & Trip Planner

A high-performance, **containerless truck trip optimization** and **Hours of Service (HOS)** simulation engine built with **Django Rest Framework (DRF)** and **React**. This platform models full Federal Motor Carrier Safety Administration (FMCSA) commercial driving compliance alongside dynamic, geo-fenced commercial fuel stops across the United States.

---
## 📊 Dashboard Preview

### 🗺️ Live Route Planning & ELD Tracking
Here is the core optimization engine in action, managing advanced spatial routes and tracking historical driving cycles:

<img width="1440" height="900" alt="image" src="https://github.com/user-attachments/assets/db96a7be-23f4-47c1-8f36-0f13d48dccbf" />



### 📈 Multi-Day Hours of Service Logs
The platform dynamically splits continuous trip timelines into exact 24-hour buckets, tracking driver compliance and delivery completion across multiple days:

<img width="1440" height="900" alt="image" src="https://github.com/user-attachments/assets/d9828db0-7ffa-4bc1-82c6-b1b09667d207" />

<img width="1440" height="900" alt="image" src="https://github.com/user-attachments/assets/bcd7b3d2-cbfa-4755-81a7-25cebcaccd25" />



---

## 🚀 Key Features

*   **🌐 Single-Call Unified Routing:** Leverages OpenRouteService (ORS) to map multi-stop pathways via a single consolidated network payload, eliminating localized routing bottlenecks.
*   **⏱️ Predictive HOS Lifecycle Simulation:** Implements precise loop-state logic tracking the 11-hour driving window, 14-hour daily duty limit, mandatory 8-hour rest breaks, and the 70-hour/8-day rolling cycle limits including dynamic 34-hour restarts.
*   **⛽ Geospatial Bounding Prefiltering:** Optimizes commercial truck stop discovery using database-level coordinate pre-filtering before executing Haversine cost-analysis formulas.
*   **📊 Interactive ELD Compliance Charts:** Visualizes standard 24-hour log charts mapping continuous driver states across the life of the shipment.

---

## 🛠️ Architecture & Tech Stack

*   **🖥️ Backend:** Python 3.9+, Django, Django Rest Framework (DRF), SQLite/PostgreSQL
*   **🎨 Frontend:** React, Tailwind CSS, Leaflet Maps
*   **🗺️ Geospatial Engines:** OpenRouteService (Directions API & Pelias Geocoding)

---

## ⚙️ Setup & Installation

### 1. 📋 Prerequisites
Ensure you have **Python 3.9+** and **Node.js** installed on your local machine.

### 2. 🔐 Environment Configuration
Create a `.env` file inside the root of your `backend/` directory to manage secrets securely:

SECRET_KEY=your_django_secret_key_here
DEBUG=True
ORS_API_KEY=your_openrouteservice_api_key_here

### 3. 🐍 Backend Setup

1. **Navigate to the backend directory:**
   cd backend

2. **Create and activate a virtual environment:**
   python3 -m venv my_venv
   source my_venv/bin/activate

3. **Install core dependencies:**
   pip install -r requirements.txt

4. **Execute database migrations and seed truck stop data:**
   python manage.py migrate
   python manage.py loaddata truck_stops.json

5. **Launch the development server:**
   python manage.py runserver

🚀 *The backend API service will now be active at http://127.0.0.1:8000/.*

### 4. ⚛️ Frontend Setup

1. **Navigate to the frontend directory:**
   cd ../frontend

2. **Install node dependencies:**
   npm install

3. **Start the Vite dashboard application:**
   npm run dev

🌐 *Open your browser and navigate to the local address provided by Vite (typically http://localhost:5173 or http://localhost:5174).*

---

## 📈 Interview Demonstration Checklist

When reviewing or presenting this codebase, note these deliberate architectural choices:

*   **⚡ Network Optimization:** The `_fetch_route` structure uses unified spatial arrays to request complete multi-stop coordinates in one pass, ensuring resilience against typical third-party rate limits.
*   **🧩 ELD Day Segmentation:** The backend features a robust integer-casting matrix inside `_split_timeline_into_days` to partition float-based continuous simulation streams cleanly into exactly 1440-minute daily slices.
*   **🛡️ Data Isolation:** Third-party vendor tokens are fully isolated from the codebase git history utilizing standard environment variables.
