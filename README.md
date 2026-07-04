# 🚚 Autonomous Logistix Dashboard & Trip Planner

A high-performance, **containerless truck trip optimization** and **Hours of Service (HOS)** simulation engine built with **Django Rest Framework (DRF)** and **React**. This platform models full Federal Motor Carrier Safety Administration (FMCSA) commercial driving compliance alongside dynamic, geo-fenced commercial fuel stops across the United States.

---
## 📊 Dashboard Preview

### 🗺️ Live Route Planning & ELD Tracking
Here is the core optimization engine in action, managing advanced spatial routes and tracking historical driving cycles:

<img width="1440" height="812" alt="E43AF5F4-153A-4940-B26D-05462CA263A6" src="https://github.com/user-attachments/assets/128e1622-1811-4c3d-bd97-c265e48e539a" />


### 📈 Multi-Day Hours of Service Logs
The platform dynamically splits continuous trip timelines into exact 24-hour buckets, tracking driver compliance and delivery completion across multiple days:

> **Sample day 1 log graph

<img width="1440" height="812" alt="1F27CCA1-818C-43AC-B342-7F28429FDF2F" src="https://github.com/user-attachments/assets/c63e1559-2522-40fb-8fd8-bc39e2c8d899" />

> **Sample day 2 log graph

<img width="1440" height="812" alt="7540D04B-3CD5-476F-932F-F6DBBD91D442" src="https://github.com/user-attachments/assets/bff2e4c5-fbc0-42b2-90c9-8e185d5cd7da" />

> **Sample day 2 & 3 log graph

<img width="1440" height="812" alt="D7ED9CBE-3810-41CC-815B-62446823F803" src="https://github.com/user-attachments/assets/369eb40c-b66a-4f38-b353-cc72b0658954" />

> **Sample day 3 & 4 log graph

<img width="1440" height="812" alt="669B54B7-6800-4E9B-B3DA-76E9B722C07B" src="https://github.com/user-attachments/assets/e3b4e737-c3bc-4a00-af37-5d62fbb022ef" />

> **Sample day 4 log graph

<img width="1440" height="812" alt="5528061C-0CB4-4320-8B8A-A662DE2D71DB" src="https://github.com/user-attachments/assets/06c1a5f3-712c-46e4-83a1-3bedd9ab8653" />





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
