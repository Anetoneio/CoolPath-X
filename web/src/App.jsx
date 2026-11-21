import { useState, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  GeoJSON,
} from 'react-leaflet';
import { API_BASE_URL, api } from './config';

// Colour ramp for heat_index_0_100 (exposure values are estimates).
function heatColor(index) {
  if (index >= 80) return '#7f0000';
  if (index >= 70) return '#ff4d4d';
  if (index >= 60) return '#ffa64d';
  if (index >= 50) return '#ffe066';
  return '#d9f2a6';
}

function style(feature) {
  const index = feature.properties?.heat_index_0_100 ?? 50;
  return {
    color: heatColor(index),
    weight: 1,
    fillColor: heatColor(index),
    fillOpacity: 0.5,
  };
}

const CENTER = [23.0225, 72.5714]; // Ahmedabad city centre

export default function App() {
  const [sites, setSites] = useState([]);
  const [heatGrid, setHeatGrid] = useState(null);
  const [heatVisible, setHeatVisible] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [sitesRes, gridRes] = await Promise.all([
          fetch(api('/sites')),
          fetch(api('/heat-grid')),
        ]);
        if (!cancelled) {
          setSites(await sitesRes.json());
          setHeatGrid(await gridRes.json());
        }
      } catch (err) {
        console.warn('Failed to load map data from engine:', err);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="flex h-screen text-slate-900">
      {/* Map panel */}
      <div className="flex-1 relative">
        <MapContainer center={CENTER} zoom={12} className="absolute inset-0">
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; OpenStreetMap contributors'
          />
          {heatVisible && heatGrid && (
            <GeoJSON data={heatGrid} style={style} />
          )}
          {sites.map((site) => (
            <Marker
              key={site.site_id}
              position={[site.lat, site.lon]}
            >
              <Popup>
                <div className="p-1">
                  <div className="font-bold">{site.name}</div>
                  <div className="text-xs text-slate-600">
                    {site.job_type} &middot; intensity: {site.intensity}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        {/* Heat-layer toggle */}
        <div className="absolute top-4 left-4 z-20 flex items-center gap-2 bg-white/90 backdrop-blur px-3 py-2 rounded-lg shadow border">
          <input
            type="checkbox"
            checked={heatVisible}
            onChange={(e) => setHeatVisible(e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Heat layer (estimate)</label>
        </div>
      </div>

      {/* Sidebar */}
      <aside className="w-80 border-l bg-white">
        <div className="p-4 border-b">
          <h1 className="text-lg font-bold">COOLPATH X</h1>
          <p className="text-sm text-slate-500">Ahmedabad · heat-aware scheduling</p>
        </div>
        <div className="h-full overflow-y-auto p-4 space-y-4">
          <Panel title="Schedule" />
          <Panel title="Route Comparison" />
          <Panel title="Data Confidence" />
        </div>
      </aside>
    </div>
  );
}

function Panel({ title }) {
  return (
    <div className="border rounded-lg p-4">
      <h2 className="font-semibold mb-2">{title}</h2>
      <div className="h-32 rounded bg-slate-100 flex items-center justify-center text-slate-400 text-sm">
        Panel content (placeholder)
      </div>
    </div>
  );
}