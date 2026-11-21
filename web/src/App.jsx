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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(typeof window !== 'undefined' && window.innerWidth < 1024);

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

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onResize = () => setIsMobile(window.innerWidth < 1024);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const handleSchedule = (result) => {
    setSchedule(result);
  };

  const handleRoutes = (routeList) => {
    setRoutes(routeList);
  };

  // On desktop (lg+) the sidebar is always visible. On mobile it's toggleable.
  const showSidebar = isMobile ? sidebarOpen : true;

  return (
    <div className="flex h-screen text-slate-900">
      {/* Map panel — always full size */}
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

        {/* Mobile sidebar toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className={`lg:hidden absolute top-4 right-4 z-30 p-3 bg-white/90 backdrop-blur rounded-lg shadow border text-slate-900 ${!showSidebar ? 'z-40' : ''}`}
          aria-label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
        >
          {sidebarOpen ? '×' : '☰'}
        </button>

        {error && (
          <div className="absolute bottom-4 left-4 z-20 p-3 rounded bg-red-50 border border-red-200 text-red-800 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Sidebar — hidden on mobile by default, toggleable; always visible on desktop */}
      {!showSidebar ? null : (
        <aside className="w-80 border-l bg-white lg:block">
          <div className="p-4 border-b flex justify-between items-start">
            <div>
              <h1 className="text-lg font-bold">COOLPATH X</h1>
              <p className="text-sm text-slate-500">Ahmedabad · heat-aware scheduling</p>
            </div>
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1 text-slate-500 hover:text-slate-900"
                aria-label="Hide sidebar"
              >
                ×
              </button>
            )}
          </div>
          <div className="h-full overflow-y-auto p-4 space-y-4">
            <SiteSelector sites={sites} onSchedule={handleSchedule} />
            <SchedulePanel schedule={schedule} sites={sites} />
            <RoutePanel sites={sites} facilities={facilities} onRoutes={handleRoutes} />
            <Panel title="Data Confidence" />
          </div>
        </aside>
      )}

      {/* Mobile sidebar backdrop */}
      {showSidebar && isMobile && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-20"
          onClick={() => setSidebarOpen(false)}
        />
      )}
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
