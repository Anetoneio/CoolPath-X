import { useState } from 'react';
import { postRouteCompare } from '../../config';

// Route comparison panel: two routes in different colors, exposure badges, nearby water points.
// All exposure_score values are estimates from the engine.
export default function RoutePanel({ sites, facilities, onRoutes }) {
  const [fromSite, setFromSite] = useState('');
  const [toSite, setToSite] = useState('');
  const [departTime, setDepartTime] = useState('09:45');
  const [loading, setLoading] = useState(false);
  const [routes, setRoutes] = useState([]);
  const [error, setError] = useState(null);

  // Build a map of facility id -> properties for water point lookups
  const facilityMap = buildFacilityMap(facilities);

  const handleCompare = async (e) => {
    e.preventDefault();
    if (!fromSite || !toSite) {
      setError('Please select both sites.');
      return;
    }
    setLoading(true);
    setError(null);
    setRoutes([]);
    try {
      const result = await postRouteCompare({
        from_site: fromSite,
        to_site: toSite,
        depart_time: departTime,
      });
      const routeList = result.routes ?? [];
      setRoutes(routeList);
      onRoutes?.(routeList);
    } catch (err) {
      console.error('Route compare failed:', err);
      setError(err.message || 'Failed to compare routes.');
    } finally {
      setLoading(false);
    }
  };

  const siteOptions = sites.map((s) => ({
    id: s.site_id,
    label: `${s.site_id} — ${s.name}`,
  }));

  const waterPointNames = (ids) => {
    if (!ids || !facilityMap) return ids;
    return ids.map((id) => {
      const f = facilityMap[id];
      return f ? `${id} (${f.type})` : id;
    });
  };

  return (
    <section className="rounded-xl border border-white/10 bg-white/5 p-3.5 space-y-3.5">
      <h2 className="text-sm font-semibold text-slate-100">Route Comparison</h2>
      <form onSubmit={handleCompare} className="space-y-3">
        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <label htmlFor="route-from" className="block text-xs text-slate-300 mb-1">
              From site
            </label>
            <select
              id="route-from"
              value={fromSite}
              onChange={(e) => setFromSite(e.target.value)}
              className="w-full rounded-lg border border-white/15 bg-slate-950/60 px-2 py-1.5 text-xs text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <option value="">Select…</option>
              {siteOptions.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="route-to" className="block text-xs text-slate-300 mb-1">
              To site
            </label>
            <select
              id="route-to"
              value={toSite}
              onChange={(e) => setToSite(e.target.value)}
              className="w-full rounded-lg border border-white/15 bg-slate-950/60 px-2 py-1.5 text-xs text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <option value="">Select…</option>
              {siteOptions.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="route-depart" className="block text-xs text-slate-300 mb-1">
            Depart time
          </label>
          <input
            id="route-depart"
            type="time"
            value={departTime}
            onChange={(e) => setDepartTime(e.target.value)}
            className="w-full rounded-lg border border-white/15 bg-slate-950/60 px-2.5 py-1.5 text-xs text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-sky-500 px-4 py-2 text-xs sm:text-sm font-semibold text-slate-950 hover:bg-sky-400 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
        >
          {loading ? 'Comparing…' : 'Compare routes'}
        </button>
      </form>

      {error && (
        <div
          role="alert"
          className="p-2.5 rounded-lg bg-red-950/80 border border-red-400/40 text-red-100 text-xs"
        >
          {error}
        </div>
      )}

      {routes.length > 0 && (
        <div className="space-y-2.5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Routes
          </h3>
          {routes.map((route) => {
            const isLower = route.id === 'R01';
            const nearby = waterPointNames(route.water_points_nearby);
            return (
              <div
                key={route.id}
                className={`rounded-lg border p-2.5 space-y-1.5 ${
                  isLower
                    ? 'border-emerald-400/35 bg-emerald-950/35'
                    : 'border-orange-400/35 bg-orange-950/35'
                }`}
              >
                <div className="flex justify-between items-start gap-2">
                  <div className="text-xs sm:text-sm font-medium text-slate-100">
                    {route.label}
                  </div>
                  <span
                    className={`text-[11px] font-medium shrink-0 ${
                      isLower ? 'text-emerald-300' : 'text-orange-300'
                    }`}
                  >
                    {isLower ? 'Lower exposure' : 'Faster / direct'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                  <div>Distance: {route.distance_km} km</div>
                  <div>Duration: {route.duration_min} min</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-200">
                    Exposure: {route.exposure_score}
                  </span>
                  <span className="text-[11px] text-amber-300 bg-amber-950/60 border border-amber-400/25 px-1.5 py-0.5 rounded">
                    (estimate)
                  </span>
                </div>
                <div className="text-xs text-slate-300">
                  Nearby water: {nearby.length > 0 ? nearby.join(', ') : 'none'}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

// Build a lookup map of facility id -> properties for water point name resolution
function buildFacilityMap(facilities) {
  if (!facilities?.features) return null;
  const map = {};
  for (const f of facilities.features) {
    map[f.properties.id] = f.properties;
  }
  return map;
}
