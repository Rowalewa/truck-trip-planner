/* eslint-disable no-unused-vars */
import React, { useState } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for missing default Leaflet icons in Vite builds
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom Component to draw the mandatory 24-Hour 4-Row ELD Grid Chart via Inline SVG
function EldGrid({ dayNumber, events }) {
  // SVG Grid Dimensions
  const svgWidth = 600;
  const svgHeight = 140;
  const labelWidth = 100;
  const chartWidth = svgWidth - labelWidth; // 500 units for 24 hours

  // Y-axis mappings for the 4 explicit HOS categories
  const rowY = {
    'Off Duty': 25,
    'Sleeper Berth': 55,
    'Driving': 85,
    'On Duty (Not Driving)': 115
  };

  // Helper function to normalize status strings from backend
  const getStatusKey = (status) => {
    if (status.includes('Driving')) return 'Driving';
    if (status.includes('Sleeper')) return 'Sleeper Berth';
    if (status.includes('On Duty')) return 'On Duty (Not Driving)';
    return 'Off Duty';
  };

  // Convert timeline minutes (0 - 1440) to SVG X-coordinates
  const getX = (minute) => labelWidth + (minute / 1440) * chartWidth;

  // Build the continuous tracking path matching assignment guidelines
  let pathD = '';
  events.forEach((evt, idx) => {
    const statusKey = getStatusKey(evt.status);
    const y = rowY[statusKey];
    const startX = getX(evt.start_minute);
    const endX = getX(evt.end_minute);

    if (idx === 0) {
      pathD += `M ${startX} ${y}`;
    } else {
      pathD += ` H ${startX}`; // Horizontal line across duration
    }
    pathD += ` H ${endX}`;

    // If there's a next event, draw a vertical line connecting to the next status row
    if (idx < events.length - 1) {
      const nextStatusKey = getStatusKey(events[idx + 1].status);
      const nextY = rowY[nextStatusKey];
      pathD += ` V ${nextY}`;
    }
  });

  // Generate grid lines for the 24 hours
  const gridLines = [];
  for (let i = 0; i <= 24; i++) {
    const x = labelWidth + (i / 24) * chartWidth;
    gridLines.push(
      <g key={i}>
        <line x1={x} y1={10} x2={x} y2={130} stroke="#e2e8f0" strokeDasharray={i % 4 === 0 ? '0' : '2'} />
        {i % 2 === 0 && <text x={x} y={138} fontSize="9" textAnchor="middle" fill="#94a3b8">{i}</text>}
      </g>
    );
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '15px', marginBottom: '20px' }}>
      <h5 style={{ margin: '0 0 10px 0', color: '#1e293b' }}>Day {dayNumber} Log Graph</h5>
      <svg width="100%" height={svgHeight} viewBox={`0 0 ${svgWidth} ${svgHeight}`}>
        {/* Row Grid Containers */}
        {Object.entries(rowY).map(([label, y]) => (
          <g key={label}>
            <text x="5" y={y + 4} fontSize="10" fontWeight="600" fill="#64748b">{label}</text>
            <line x1={labelWidth} y1={y} x2={svgWidth} y2={y} stroke="#f1f5f9" strokeWidth="1" />
          </g>
        ))}
        {/* 24-Hour Vertical Grid Markers */}
        {gridLines}
        {/* Continuous HOS Compliance Log Line Path */}
        {pathD && <path d={pathD} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />}
      </svg>
    </div>
  );
}

export default function App() {
  const [formData, setFormData] = useState({
    current_location: 'Oklahoma City, OK',
    pickup_location: 'Tomah, WI',
    dropoff_location: 'Gila Bend, AZ',
    cycle_hours_used: 0
  });

  const [tripData, setTripData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/plan-trip/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        setTripData(data);
      }
    } catch (err) {
      setError('Cannot establish network link to optimization engine backend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'sans-serif', backgroundColor: '#f4f6f9', margin: 0 }}>
      <header style={{ background: '#1e293b', color: '#fff', padding: '15px 20px', fontWeight: 'bold', fontSize: '18px' }}>
        🚚 Autonomous Logistix Dashboard
      </header>

      <div style={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
        {/* Left Input & Custom ELD Graph Panel */}
        <aside style={{ width: '450px', background: '#fff', padding: '20px', overflowY: 'auto', boxShadow: '2px 0 5px rgba(0,0,0,0.05)', zIndex: 10 }}>
          <h3 style={{ marginTop: 0 }}>Create Optimization Run</h3>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', marginBottom: '4px' }}>Current Location</label>
              <input type="text" value={formData.current_location} onChange={e => setFormData({...formData, current_location: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box' }} required />
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', marginBottom: '4px' }}>Pickup Point</label>
              <input type="text" value={formData.pickup_location} onChange={e => setFormData({...formData, pickup_location: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box' }} required />
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', marginBottom: '4px' }}>Dropoff Destination</label>
              <input type="text" value={formData.dropoff_location} onChange={e => setFormData({...formData, dropoff_location: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box' }} required />
            </div>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', marginBottom: '4px' }}>Cycle Hours Used</label>
              <input type="number" value={formData.cycle_hours_used} onChange={e => setFormData({...formData, cycle_hours_used: parseInt(e.target.value) || 0})} style={{ width: '100%', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px', boxSizing: 'border-box' }} />
            </div>
            <button type="submit" disabled={loading} style={{ width: '100%', background: '#2563eb', color: '#fff', border: 'none', padding: '12px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>
              {loading ? 'Processing Route Matrix...' : 'Generate Plan'}
            </button>
          </form>

          {error && <div style={{ color: '#ef4444', marginTop: '15px' }}>⚠️ {error}</div>}

          {tripData && (
            <div style={{ marginTop: '20px' }}>
              {/* Updated Metrics Box featuring the Spotter required Fuel Cost */}
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '15px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between' }}>
                <div>
                  <small style={{ color: '#64748b', display: 'block' }}>Distance</small>
                  <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{Math.round(tripData.total_distance_miles)} mi</div>
                </div>
                <div>
                  <small style={{ color: '#64748b', display: 'block' }}>Duration</small>
                  <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{Math.round(tripData.total_duration_hours)} hrs</div>
                </div>
                <div>
                  <small style={{ color: '#64748b', display: 'block' }}>Est. Fuel Cost</small>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#10b981' }}>${tripData.total_fuel_cost}</div>
                </div>
              </div>

              <h4>Hours of Service Grid Logs</h4>
              {Object.keys(tripData.eld_days).sort((a,b)=>a-b).map(dayNum => (
                <EldGrid key={dayNum} dayNumber={dayNum} events={tripData.eld_days[dayNum]} />
              ))}
            </div>
          )}
        </aside>

        {/* Right Dynamic Map Panel */}
        <main style={{ flexGrow: 1, position: 'relative', height: '100%' }}>
          <MapContainer center={[37.8, -96]} zoom={4} style={{ width: '100%', height: '100%' }}>
            <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {tripData && tripData.route_geometry && (
              <Polyline positions={tripData.route_geometry} color="#2563eb" weight={5} opacity={0.75} />
            )}
            {tripData && tripData.markers.map((marker, idx) => {
              // Define custom colors matching the assignment specification
              let pinColor = '#64748b'; // Default Grey
              if (marker.type === 'origin') pinColor = '#10b981';   // Green for Start
              if (marker.type === 'pickup') pinColor = '#f59e0b';   // Orange for Pickup
              if (marker.type === 'dropoff') pinColor = '#ef4444';  // Red for Dropoff
              if (marker.type === 'fuel') pinColor = '#3b82f6';     // Vibrant Blue for Fuel Stops

              const customHtmlIcon = L.divIcon({
                className: 'custom-route-pin',
                html: `<div style="
                  background-color: ${pinColor}; 
                  width: 16px; 
                  height: 16px; 
                  border-radius: 50%; 
                  border: 2px solid white; 
                  box-shadow: 0 0 6px rgba(0,0,0,0.4);
                "></div>`,
                iconSize: [16, 16],
                iconAnchor: [8, 8],
              });

              return (
                <Marker key={idx} position={marker.coords} icon={customHtmlIcon}>
                  <Popup>
                    <strong>{marker.name}</strong><br/>
                    <span style={{ color: '#64748b', textTransform: 'uppercase', fontSize: '11px', fontWeight: 'bold' }}>
                      Type: {marker.type}
                    </span>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
        </main>
      </div>
    </div>
  );
}