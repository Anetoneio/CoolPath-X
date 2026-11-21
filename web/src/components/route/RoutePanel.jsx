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
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const siteOptions = sites.map((s) => ({ id: s.site_id, label: `${s.site_id} — ${s.name}` }));

  const waterPointNames = (ids) => {
    if (!ids || !facilityMap) return ids;
    return ids.map((id) => {
      const f = facilityMap[id];
      return f ? `${id} (${f.type})` : id;
    });
  };

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Route Comparison</h2>
      <form onSubmit={handleCompare} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">From site</label>
            <select
              value={fromSite}
              onChange={(e) => setFromSite(e.target.value)}
              className="w-full border rounded px-2 py-1 text-sm"
            >
              <option value="">Select…</option>
              {siteOptions.map((o) => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">To site</label>
            <select
              value={toSite}
              onChange={(e) => setToSite(e.target.value)}
              className="w-full border rounded px-2 py-1 text-sm"
            >
              <option value="">Select…</option>
              {siteOptions.map((o) => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Depart time</label>
          <input
            type="time"
            value={departTime}
            onChange={(e) => setDepartTime(e.target.value)}
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-slate-900 text-white px-4 py-2 rounded disabled:bg-slate-400 text-sm font-medium"
        >
          {loading ? 'Comparing…' : 'Compare routes'}
        </button>
      </form>

      {error && (
        <div className="p-2 rounded bg-red-50 border border-red-200 text-red-800 text-sm">
          {error}
        </div>
      )}

      {routes.length > 0 && (
        <div className="border rounded p-3 bg-slate-50 space-y-3">
          <h3 className="font-semibold text-slate-900">Routes</h3>
          {routes.map((route) => {
            const isLower = route.id === 'R01';
            const nearby = waterPointNames(route.water_points_nearby);
            return (
              <div key={route.id} className={`border rounded p-2 ${isLower ? 'border-green-200 bg-green-5' : 'border-orange-200 bg-orange-5'}`}>
                <div className="flex justify-between items-start mb-1">
                  <div className="font-medium">{route.label}</div>
                  <span className={`text-xs font-medium ${isLower ? 'text-green-700' : 'text-orange-700'}`}>
                    {isLower ? 'Lower exposure' : 'Faster / direct'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 mb-1">
                  <div>Distance: {route.distance_km} km</div>
                  <div>Duration: {route.duration_min} min</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium">Exposure: {route.exposure_score}</span>
                  <span className="text-[10px] text-orange-500 bg-orange-100 px-1.5 py-0.5 rounded">(estimate)</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Nearby water: {nearby.length > 0 ? nearby.join(', ') : 'none'}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
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