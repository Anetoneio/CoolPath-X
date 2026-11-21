import { useState, useEffect } from 'react';
import MapView from './components/map/MapView';
import SiteSelector from './components/site/SiteSelector';
import SchedulePanel from './components/schedule/SchedulePanel';
import RoutePanel from './components/route/RoutePanel';
import {
  getSites,
  getFacilities,
  getHeatGrid,
} from './config';

const CENTER = [23.0225, 72.5714]; // Ahmedabad city centre

export default function App() {
  const [sites, setSites] = useState([]);
  const [facilities, setFacilities] = useState(null);
  const [heatGrid, setHeatGrid] = useState(null);
  const [heatVisible, setHeatVisible] = useState(false);
  const [routes, setRoutes] = useState([]);
  const [schedule, setSchedule] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [sitesData, facilitiesData, heatGridData] = await Promise.all([
          getSites(),
          getFacilities(),
          getHeatGrid(),
        ]);
        if (!cancelled) {
          setSites(sitesData);
          setFacilities(facilitiesData);
          setHeatGrid(heatGridData);
        }
      } catch (err) {
        if (!cancelled) {
          console.warn('Failed to load map data from engine:', err);
          setError(err.message);
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleSchedule = (result) => {
    setSchedule(result);
  };

  const handleRoutes = (routeList) => {
    setRoutes(routeList);
  };

  return (
    <div className="flex h-screen text-slate-900">
      {/* Map panel */}
      <div className="flex-1 relative">
        <MapView
          sites={sites}
          facilities={facilities}
          heatGrid={heatGrid}
          heatVisible={heatVisible}
          routes={routes}
        />

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

        {error && (
          <div className="absolute bottom-4 left-4 z-20 p-3 rounded bg-red-50 border border-red-200 text-red-800 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Sidebar */}
      <aside className="w-80 border-l bg-white">
        <div className="p-4 border-b">
          <h1 className="text-lg font-bold">COOLPATH X</h1>
          <p className="text-sm text-slate-500">Ahmedabad · heat-aware scheduling</p>
        </div>
        <div className="h-full overflow-y-auto p-4 space-y-4">
          <SiteSelector sites={sites} onSchedule={handleSchedule} />
          <SchedulePanel schedule={schedule} sites={sites} />
          <RoutePanel sites={sites} facilities={facilities} onRoutes={handleRoutes} />
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
