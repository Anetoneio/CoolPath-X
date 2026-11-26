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

export default function App() {
  const [sites, setSites] = useState([]);
  const [facilities, setFacilities] = useState(null);
  const [heatGrid, setHeatGrid] = useState(null);
  const [heatVisible, setHeatVisible] = useState(false);
  const [routes, setRoutes] = useState([]);
  const [schedule, setSchedule] = useState(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [wakingUp, setWakingUp] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(typeof window !== 'undefined' && window.innerWidth < 1024);

  useEffect(() => {
    let cancelled = false;
    const wakeTimer = setTimeout(() => {
      if (!cancelled) {
        setWakingUp(true);
      }
    }, 3000);

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
          setError(err.message || 'Unable to load map data from engine.');
        }
      } finally {
        clearTimeout(wakeTimer);
        if (!cancelled) {
          setWakingUp(false);
          setLoadingInitial(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      clearTimeout(wakeTimer);
    };
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

  // On desktop (lg+) the floating panel is always visible. On mobile it's toggleable.
  const showSidebar = isMobile ? sidebarOpen : true;

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* Full-bleed dark map */}
      <MapView
        sites={sites}
        facilities={facilities}
        heatGrid={heatGrid}
        heatVisible={heatVisible}
        routes={routes}
      />

      {/* Heat-layer toggle & continuous legend — offset from top-left zoom controls */}
      <div className="absolute top-3 left-14 z-20 max-w-[calc(100vw-8.25rem)] sm:max-w-xs rounded-2xl bg-slate-900/75 backdrop-blur-md border border-white/15 shadow-2xl px-3.5 py-2.5">
        <label
          htmlFor="heat-layer-toggle"
          className="flex items-center gap-2.5 cursor-pointer select-none"
        >
          <input
            id="heat-layer-toggle"
            type="checkbox"
            checked={heatVisible}
            onChange={(e) => setHeatVisible(e.target.checked)}
            className="h-4 w-4 rounded border-white/30 bg-slate-950/70 text-sky-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
          />
          <span className="text-xs sm:text-sm font-medium text-slate-100">
            Heat layer (estimate)
          </span>
        </label>

        {heatVisible && (
          <div className="mt-2.5 pt-2.5 border-t border-white/10 space-y-1.5">
            <div className="text-[11px] font-medium text-slate-200">
              Estimated heat index
            </div>
            <div
              className="h-2.5 w-full rounded-full border border-white/15"
              style={{
                background:
                  'linear-gradient(to right, #38bdf8 0%, #34d399 25%, #facc15 50%, #f97316 75%, #dc2626 100%)',
              }}
              aria-hidden="true"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-300">
              <span>0</span>
              <span>25</span>
              <span>50</span>
              <span>75</span>
              <span>100</span>
            </div>
          </div>
        )}
      </div>

      {/* Mobile drawer toggle — top-right, never overlaps top-left zoom or bottom-right attribution */}
      <button
        type="button"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden absolute top-3 right-3 z-40 h-10 w-10 flex items-center justify-center rounded-xl bg-slate-900/80 backdrop-blur-md border border-white/15 shadow-2xl text-slate-100 hover:bg-slate-800/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        aria-label={sidebarOpen ? 'Hide control panel' : 'Show control panel'}
        aria-expanded={sidebarOpen}
      >
        <span className="text-lg leading-none" aria-hidden="true">
          {sidebarOpen ? '×' : '☰'}
        </span>
      </button>

      {/* Engine waking-up notice (only if initial request is still pending after ~3s) */}
      {loadingInitial && wakingUp && !error && (
        <div
          role="status"
          aria-live="polite"
          className="absolute bottom-11 left-3 right-3 sm:right-auto sm:max-w-sm lg:left-4 z-20 rounded-xl bg-slate-900/85 backdrop-blur-md border border-sky-400/30 shadow-2xl px-3.5 py-2.5 text-xs sm:text-sm text-sky-100 flex items-center gap-2.5"
        >
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-full bg-sky-400 animate-pulse"
            aria-hidden="true"
          />
          <span>Engine is waking up, this can take about a minute</span>
        </div>
      )}

      {/* Initial load error banner */}
      {error && (
        <div
          role="alert"
          className="absolute bottom-11 left-3 right-3 sm:right-auto sm:max-w-md lg:left-4 z-20 rounded-xl bg-red-950/85 backdrop-blur-md border border-red-400/40 shadow-2xl px-3.5 py-2.5 text-xs sm:text-sm text-red-100"
        >
          <span className="font-semibold">Engine error: </span>
          <span>{error}</span>
        </div>
      )}

      {/* Basemap terms & attribution link on page (clear of Leaflet bottom-right attribution) */}
      <div className="absolute bottom-2 left-3 z-20 rounded-lg bg-slate-900/75 backdrop-blur-md border border-white/10 px-2.5 py-1 text-[11px] text-slate-300">
        <span>Basemap: CARTO Dark Matter &middot; </span>
        <a
          href="https://carto.com/legal/basemap-terms/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sky-300 underline hover:text-sky-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 rounded"
        >
          Terms
        </a>
      </div>

      {/* Mobile backdrop */}
      {showSidebar && isMobile && (
        <div
          className="lg:hidden fixed inset-0 bg-slate-950/40 z-20"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Floating glass panel — positioned between top-16 and bottom-9 on mobile so zoom & attribution remain uncovered */}
      {showSidebar && (
        <aside
          aria-label="Scheduling and routing controls"
          className="fixed top-16 bottom-9 left-3 right-3 lg:left-auto lg:top-4 lg:right-4 lg:bottom-9 lg:w-96 z-30 flex flex-col rounded-2xl bg-slate-900/78 backdrop-blur-md border border-white/15 shadow-2xl overflow-hidden"
        >
          <div className="px-4 py-3.5 border-b border-white/10 flex justify-between items-start gap-3 shrink-0">
            <div>
              <h1 className="text-base font-bold tracking-tight text-white">
                COOLPATH X
              </h1>
              <p className="text-xs text-slate-300">
                Ahmedabad &middot; heat-aware scheduling
              </p>
            </div>
            {isMobile && (
              <button
                type="button"
                onClick={() => setSidebarOpen(false)}
                className="h-8 w-8 flex items-center justify-center rounded-lg text-slate-300 hover:text-white hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                aria-label="Hide control panel"
              >
                <span className="text-lg leading-none" aria-hidden="true">×</span>
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <SiteSelector sites={sites} onSchedule={handleSchedule} />
            <SchedulePanel schedule={schedule} sites={sites} />
            <RoutePanel sites={sites} facilities={facilities} onRoutes={handleRoutes} />
            <Panel title="Data Confidence" />
          </div>
        </aside>
      )}
    </div>
  );
}

function Panel({ title }) {
  return (
    <section className="rounded-xl border border-white/10 bg-white/5 p-3.5">
      <h2 className="text-sm font-semibold text-slate-100 mb-2">{title}</h2>
      <div className="h-24 rounded-lg bg-slate-950/50 border border-white/5 flex items-center justify-center text-slate-400 text-xs">
        Panel content (placeholder)
      </div>
    </section>
  );
}
