/* eslint-disable react-hooks/set-state-in-effect */
/* eslint-disable no-useless-assignment */
/* eslint-disable no-unused-vars */
import React, { useState, useEffect, useRef } from 'react';
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

// Always-Active, Ultra-Responsive Autocomplete Input Component
function CityAutocompleteInput({ label, value, onChange, citiesList, isCsvLoading }) {
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (text) => {
    onChange(text);
    
    const query = text.trim().toLowerCase();
    
    let matches = [];
    if (query === '') {
      matches = citiesList.slice(0, 8); 
    } else {
      matches = citiesList.filter(city => 
        city.toLowerCase().includes(query)
      ).slice(0, 8);
    }

    setSuggestions(matches);
    setShowDropdown(true);
  };

  return (
    <div ref={containerRef} style={{ marginBottom: '12px', position: 'relative' }}>
      <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '4px' }}>
        {label}
      </label>
      <input 
        type="text" 
        value={value} 
        disabled={isCsvLoading}
        onChange={e => handleInputChange(e.target.value)} 
        onFocus={() => handleInputChange(value)}
        style={{ 
          width: '100%', 
          padding: '10px', 
          border: '1px solid #334155', 
          borderRadius: '6px', 
          boxSizing: 'border-box',
          backgroundColor: '#1e293b',
          color: '#fff',
          fontSize: '14px',
          opacity: isCsvLoading ? 0.6 : 1
        }} 
        placeholder={isCsvLoading ? "Streaming US location database..." : "Search US cities..."}
        required 
      />
      {showDropdown && (
        <ul style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '6px',
          marginTop: '4px',
          padding: 0,
          listStyle: 'none',
          maxHeight: '180px',
          overflowY: 'auto',
          zIndex: 99999,
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
        }}>
          {suggestions.length > 0 ? (
            suggestions.map((place, i) => (
              <li 
                key={i} 
                onClick={() => {
                  onChange(place);
                  setShowDropdown(false);
                }}
                style={{ 
                  padding: '10px 12px', 
                  cursor: 'pointer', 
                  fontSize: '13px', 
                  borderBottom: '1px solid #334155', 
                  color: '#e2e8f0',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
                onMouseEnter={e => e.target.style.background = '#334155'}
                onMouseLeave={e => e.target.style.background = '#1e293b'}
              >
                📍 {place}
              </li>
            ))
          ) : (
            <li style={{ padding: '10px 12px', fontSize: '13px', color: '#ef4444', fontStyle: 'italic', fontWeight: 'bold' }}>
              ❌ No matching US cities found
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

// Custom 24-Hour ELD Grid Line Graph Renderer
function formatTime(minuteOfDay) {
  const h = Math.floor(minuteOfDay / 60) % 24;
  const m = Math.round(minuteOfDay % 60);
  const period = h < 12 ? 'AM' : 'PM';
  const displayH = h % 12 === 0 ? 12 : h % 12;
  return `${displayH}:${String(m).padStart(2, '0')} ${period}`;
}

function EldGrid({ dayNumber, events, dailySummary }) {
  const svgWidth = 600;
  const svgHeight = 140;
  const labelWidth = 100;
  const chartWidth = svgWidth - labelWidth;

  const rowY = {
    'Off Duty': 25,
    'Sleeper Berth': 55,
    'Driving': 85,
    'On Duty (Not Driving)': 115
  };

  const getStatusKey = (status) => {
    if (status.includes('On Duty')) return 'On Duty (Not Driving)';
    if (status.includes('Sleeper')) return 'Sleeper Berth';
    if (status.includes('Driving')) return 'Driving';
    return 'Off Duty';
  };

  const getX = (minute) => labelWidth + (minute / 1440) * chartWidth;

  let pathD = '';
  events.forEach((evt, idx) => {
    const statusKey = getStatusKey(evt.status);
    const y = rowY[statusKey];
    const startX = getX(evt.start_minute);
    const endX = getX(evt.end_minute);

    if (idx === 0) {
      pathD += `M ${startX} ${y}`;
    } else {
      pathD += ` H ${startX}`;
    }
    pathD += ` H ${endX}`;

    if (idx < events.length - 1) {
      const nextStatusKey = getStatusKey(events[idx + 1].status);
      const nextY = rowY[nextStatusKey];
      pathD += ` V ${nextY}`;
    }
  });

  const gridLines = [];
  for (let i = 0; i <= 24; i++) {
    const x = labelWidth + (i / 24) * chartWidth;
    gridLines.push(
      <g key={i}>
        <line x1={x} y1={10} x2={x} y2={130} stroke="#e2e8f0" strokeDasharray={i % 4 === 0 ? '0' : '2'} />
        {i % 2 === 0 && <text x={x} y={138} fontSize="9" textAnchor="middle" fill="#94a3b8">{i === 24 ? 'Mid' : i}</text>}
      </g>
    );
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '15px', marginBottom: '20px' }}>
      <h5 style={{ margin: '0 0 10px 0', color: '#1e293b' }}>Day {dayNumber} Log Graph</h5>
      <svg width="100%" height={svgHeight} viewBox={`0 0 ${svgWidth} ${svgHeight}`}>
        {Object.entries(rowY).map(([label, y]) => (
          <g key={label}>
            <text x="5" y={y + 4} fontSize="10" fontWeight="600" fill="#64748b">{label}</text>
            <line x1={labelWidth} y1={y} x2={svgWidth} y2={y} stroke="#f1f5f9" strokeWidth="1" />
            {dailySummary && (
              <text x={svgWidth - 5} y={y + 4} fontSize="10" fontWeight="600" textAnchor="end" fill="#334155">
                {(dailySummary[label] / 60).toFixed(2)}h
              </text>
            )}
          </g>
        ))}
        {gridLines}
        {pathD && <path d={pathD} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />}
      </svg>

      <table style={{ width: '100%', marginTop: '12px', borderCollapse: 'collapse', fontSize: '12px' }}>
        <thead>
          <tr style={{ textAlign: 'left', color: '#64748b' }}>
            <th style={{ padding: '4px 8px', borderBottom: '1px solid #e2e8f0' }}>Time</th>
            <th style={{ padding: '4px 8px', borderBottom: '1px solid #e2e8f0' }}>Status</th>
            <th style={{ padding: '4px 8px', borderBottom: '1px solid #e2e8f0' }}>Remarks</th>
          </tr>
        </thead>
        <tbody>
          {events.map((evt, idx) => (
            <tr key={idx}>
              <td style={{ padding: '4px 8px', borderBottom: '1px solid #f1f5f9', whiteSpace: 'nowrap' }}>
                {formatTime(evt.start_minute)}
              </td>
              <td style={{ padding: '4px 8px', borderBottom: '1px solid #f1f5f9', whiteSpace: 'nowrap' }}>
                {evt.status}
              </td>
              <td style={{ padding: '4px 8px', borderBottom: '1px solid #f1f5f9' }}>
                {evt.remark}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [citiesList, setCitiesList] = useState([]);
  const [isCsvLoading, setIsCsvLoading] = useState(true);
  const [formData, setFormData] = useState({
    current_location: 'Oklahoma City, OK',
    pickup_location: 'Tomah, WI',
    dropoff_location: 'Gila Bend, AZ',
    cycle_hours_used: 0
  });

  const [tripData, setTripData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const parseCsvData = (csvText) => {
    const lines = csvText.split('\n').map(l => l.trim()).filter(Boolean);
    if (lines.length < 2) return [];

    const headers = lines[0].split(',').map(h => h.replace(/^["']|["']$/g, '').trim().toLowerCase());
    
    let cityIdx = headers.findIndex(h => h.includes('city'));
    let stateIdx = headers.findIndex(h => h.includes('state') || h.includes('code'));

    if (cityIdx === -1) cityIdx = 3; 
    if (stateIdx === -1) stateIdx = 1;

    const parsedUnique = new Set();
    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(',');
      if (cols.length > Math.max(cityIdx, stateIdx)) {
        const city = cols[cityIdx].replace(/^["']|["']$/g, '').trim();
        const state = cols[stateIdx].replace(/^["']|["']$/g, '').trim();
        if (city && state && state.length === 2) {
          parsedUnique.add(`${city}, ${state.toUpperCase()}`);
        }
      }
    }
    return Array.from(parsedUnique).sort();
  };

  useEffect(() => {
    setIsCsvLoading(true);
    
    fetch('/us_cities_ref.csv')
      .then(res => {
        if (!res.ok) throw new Error("Local file missing.");
        return res.text();
      })
      .then(text => {
        const data = parseCsvData(text);
        if (data.length === 0) throw new Error("Empty parse.");
        setCitiesList(data);
        setIsCsvLoading(false);
      })
      .catch(() => {
        fetch('https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_cities.csv')
          .then(res => {
            if (!res.ok) throw new Error("Network streaming failed.");
            return res.text();
          })
          .then(text => {
            const data = parseCsvData(text);
            setCitiesList(data);
            setIsCsvLoading(false);
          })
          .catch(err => {
            console.error(err);
            setError("Critical Failure: Unable to fetch US locations database.");
            setIsCsvLoading(false);
          });
      });
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const normalize = (str) => str.trim().toLowerCase();
    
    const currentLoc = normalize(formData.current_location);
    const pickupLoc = normalize(formData.pickup_location);
    const dropoffLoc = normalize(formData.dropoff_location);

    if (pickupLoc === dropoffLoc) {
      setError("Invalid Route: Pickup point and Dropoff destination cannot be identical.");
      setTripData(null);
      setLoading(false);
      return;
    }

    const activeValidSet = new Set(citiesList.map(c => normalize(c)));
    const isCurrentValid = activeValidSet.has(currentLoc);
    const isPickupValid = activeValidSet.has(pickupLoc);
    const isDropoffValid = activeValidSet.has(dropoffLoc);

    if (!isCurrentValid || !isPickupValid || !isDropoffValid) {
      setError("No route for you! Enter a valid location in the US.");
      setTripData(null); 
      setLoading(false);
      return;
    }

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${API_URL}/api/plan-trip/`, {
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'sans-serif', backgroundColor: '#0f172a', margin: 0, color: '#fff' }}>
      <header style={{ background: '#1e293b', color: '#fff', padding: '15px 20px', fontWeight: 'bold', fontSize: '18px', borderBottom: '1px solid #334155' }}>
        🚚 Autonomous Logistix Dashboard
      </header>

      <div style={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
        <aside style={{ width: '450px', background: '#0f172a', padding: '20px', overflowY: 'auto', borderRight: '1px solid #334155', zIndex: 10 }}>
          <h3 style={{ marginTop: 0, color: '#f8fafc' }}>Create Optimization Run</h3>
          <form onSubmit={handleSubmit}>
            
            <CityAutocompleteInput 
              label="Current Location"
              value={formData.current_location}
              onChange={val => setFormData({...formData, current_location: val})}
              citiesList={citiesList}
              isCsvLoading={isCsvLoading}
            />

            <CityAutocompleteInput 
              label="Pickup Point"
              value={formData.pickup_location}
              onChange={val => setFormData({...formData, pickup_location: val})}
              citiesList={citiesList}
              isCsvLoading={isCsvLoading}
            />

            <CityAutocompleteInput 
              label="Dropoff Destination"
              value={formData.dropoff_location}
              onChange={val => setFormData({...formData, dropoff_location: val})}
              citiesList={citiesList}
              isCsvLoading={isCsvLoading}
            />

            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '4px' }}>Cycle Hours Used</label>
              <input 
                type="number" 
                value={formData.cycle_hours_used} 
                onChange={e => setFormData({...formData, cycle_hours_used: parseInt(e.target.value) || 0})} 
                style={{ width: '100%', padding: '10px', border: '1px solid #334155', borderRadius: '6px', boxSizing: 'border-box', backgroundColor: '#1e293b', color: '#fff' }} 
              />
            </div>
            
            <button type="submit" disabled={loading || isCsvLoading} style={{ width: '100%', background: '#2563eb', color: '#fff', border: 'none', padding: '12px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>
              {loading ? 'Processing Route Matrix...' : 'Generate Plan'}
            </button>
          </form>

          {error && (
            <div style={{ 
              color: '#ef4444', 
              marginTop: '15px', 
              background: 'rgba(239, 68, 68, 0.1)', 
              padding: '12px', 
              borderRadius: '6px', 
              border: '1px solid rgba(239, 68, 68, 0.3)',
              fontWeight: '600'
            }}>
              ⚠️ {error}
            </div>
          )}

          {tripData && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '15px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between' }}>
                <div>
                  <small style={{ color: '#94a3b8', display: 'block' }}>Distance</small>
                  <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{Math.round(tripData.total_distance_miles)} mi</div>
                </div>
                <div>
                  <small style={{ color: '#94a3b8', display: 'block' }}>Duration</small>
                  <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{Math.round(tripData.total_duration_hours)} hrs</div>
                </div>
                <div>
                  <small style={{ color: '#94a3b8', display: 'block' }}>Est. Fuel Cost</small>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#10b981' }}>${Number(tripData.total_fuel_cost).toFixed(2)}</div>
                </div>
              </div>

              <h4 style={{ color: '#f8fafc' }}>Hours of Service Grid Logs</h4>
              {Object.keys(tripData.eld_days).sort((a,b)=>a-b).map(dayNum => (
                <EldGrid
                  key={dayNum}
                  dayNumber={dayNum}
                  events={tripData.eld_days[dayNum]}
                  dailySummary={tripData.daily_summaries ? tripData.daily_summaries[dayNum] : null}
                />
              ))}
            </div>
          )}
        </aside>

        <main style={{ flexGrow: 1, position: 'relative', height: '100%' }}>
          <div style={{
            position: 'absolute',
            bottom: '24px',
            left: '24px',
            background: '#1e293b',
            padding: '12px 16px',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            zIndex: 1000,
            fontFamily: 'sans-serif',
            fontSize: '12px',
            border: '1px solid #334155',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ fontWeight: 'bold', color: '#94a3b8', marginBottom: '2px', textTransform: 'uppercase', fontSize: '10px', letterSpacing: '0.5px' }}>Route Legend</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#10b981', border: '1px solid #fff' }}></div>
              <span style={{ color: '#e2e8f0', fontWeight: '500' }}>Current Location (Start)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#f59e0b', border: '1px solid #fff' }}></div>
              <span style={{ color: '#e2e8f0', fontWeight: '500' }}>Pickup Point</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ef4444', border: '1px solid #fff' }}></div>
              <span style={{ color: '#e2e8f0', fontWeight: '500' }}>Dropoff Destination</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#3b82f6', border: '1px solid #fff' }}></div>
              <span style={{ color: '#e2e8f0', fontWeight: '500' }}>Optimized Fuel Stops</span>
            </div>
          </div>

          <MapContainer center={[37.8, -96]} zoom={4} style={{ width: '100%', height: '100%' }}>
            <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {tripData && tripData.route_geometry && (
              <Polyline positions={tripData.route_geometry} color="#2563eb" weight={5} opacity={0.75} />
            )}
            
            {/* Coordinate Collator Engine */}
            {tripData && (() => {
              const uniquePoints = [];
              tripData.markers.forEach((marker) => {
                const existing = uniquePoints.find(
                  p => p.coords[0] === marker.coords[0] && p.coords[1] === marker.coords[1]
                );
                if (existing) {
                  if (!existing.types.includes(marker.type)) existing.types.push(marker.type);
                  if (!existing.names.includes(marker.name)) existing.names.push(marker.name);
                } else {
                  uniquePoints.push({
                    coords: marker.coords,
                    types: [marker.type],
                    names: [marker.name]
                  });
                }
              });

              return uniquePoints.map((point, idx) => {
                let backgroundStyle = '#64748b';
                
                // Intelligently generate split linear gradients for overlapping location states
                if (point.types.includes('origin') && point.types.includes('pickup')) {
                  backgroundStyle = 'linear-gradient(135deg, #10b981 50%, #f59e0b 50%)';
                } else if (point.types.includes('origin')) {
                  backgroundStyle = '#10b981';
                } else if (point.types.includes('pickup')) {
                  backgroundStyle = '#f59e0b';
                } else if (point.types.includes('dropoff')) {
                  backgroundStyle = '#ef4444';
                } else if (point.types.includes('fuel')) {
                  backgroundStyle = '#3b82f6';
                }

                const customHtmlIcon = L.divIcon({
                  className: 'custom-route-pin',
                  html: `<div style="background: ${backgroundStyle}; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 6px rgba(0,0,0,0.4);"></div>`,
                  iconSize: [16, 16],
                  iconAnchor: [8, 8],
                });

                return (
                  <Marker key={idx} position={point.coords} icon={customHtmlIcon}>
                    <Popup>
                      <strong>{point.names.join(' / ')}</strong><br/>
                      <span style={{ color: '#64748b', textTransform: 'uppercase', fontSize: '11px', fontWeight: 'bold' }}>
                        Type: {point.types.join(' + ')}
                      </span>
                    </Popup>
                  </Marker>
                );
              });
            })()}
          </MapContainer>
        </main>
      </div>
    </div>
  );
}