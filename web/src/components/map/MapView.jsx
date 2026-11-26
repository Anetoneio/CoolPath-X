import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  GeoJSON,
  CircleMarker,
  Polyline,
} from 'react-leaflet';

// TODO-VERIFY: Confirm CARTO Basemaps production terms & key requirement before launch.
// Terms URL: https://carto.com/legal/basemap-terms/
// Attribution URL: https://carto.com/attributions
// Search summary indicates free tier up to 5M non-commercial / 1M commercial tile requests/month
// and notes an API key (?key=...) may be required; full verbatim terms text is UNVERIFIED.
const BASEMAP_KEY = import.meta.env.VITE_BASEMAP_KEY;
const BASEMAP_URL = BASEMAP_KEY
  ? `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=${BASEMAP_KEY}`
  : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

// Continuous cool-to-hot color ramp for heat_index_0_100 (exposure values are estimates).
// Tuned for high contrast on the dark CARTO basemap.
function heatColor(index) {
  if (index >= 80) return '#dc2626';
  if (index >= 70) return '#f97316';
  if (index >= 60) return '#facc15';
  if (index >= 50) return '#34d399';
  return '#38bdf8';
}

function heatStyle(feature) {
  const index = feature.properties?.heat_index_0_100 ?? 50;
  const color = heatColor(index);
  return {
    color,
    weight: 1.5,
    opacity: 0.85,
    fillColor: color,
    fillOpacity: 0.52,
  };
}

const CENTER = [23.0225, 72.5714]; // Ahmedabad city centre [lat, lng]

// API returns GeoJSON [lng, lat]; Leaflet uses [lat, lng].
function toLatLng(coords) {
  return [coords[1], coords[0]];
}

function toLatLngs(coords) {
  return coords.map(toLatLng);
}

// Facility marker style: verified vs unverified styled differently.
// Water = blue, shade = green. Verified = solid fill; unverified = dashed + low fill opacity.
function facilityStyle(feature) {
  const props = feature.properties || {};
  const isWater = props.type === 'water';
  const isVerified = props.verified === true;
  const baseColor = isWater ? '#38bdf8' : '#4ade80';
  return {
    radius: 8,
    color: baseColor,
    weight: 2,
    fillColor: baseColor,
    fillOpacity: isVerified ? 0.75 : 0.2,
    dashArray: isVerified ? undefined : '5, 5',
  };
}

export default function MapView({ sites, facilities, heatGrid, heatVisible, routes }) {
  const facilityFeatures = facilities?.features ?? [];

  return (
    <MapContainer center={CENTER} zoom={12} className="absolute inset-0">
      <TileLayer
        url={BASEMAP_URL}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        subdomains="abcd"
        maxZoom={20}
      />

      {/* Heat layer (estimate) */}
      {heatVisible && heatGrid && (
        <GeoJSON data={heatGrid} style={heatStyle} />
      )}

      {/* Facility markers — verified vs unverified styled differently */}
      {facilityFeatures.map((feature) => {
        const props = feature.properties || {};
        const style = facilityStyle(feature);
        const position = toLatLng(feature.geometry.coordinates);
        const isVerified = props.verified === true;
        return (
          <CircleMarker
            key={props.id}
            center={position}
            radius={style.radius}
            color={style.color}
            weight={style.weight}
            fillColor={style.fillColor}
            fillOpacity={style.fillOpacity}
            dashArray={style.dashArray}
          >
            <Popup>
              <div className="p-1 space-y-0.5">
                <div className="font-semibold text-slate-100">{props.id}</div>
                <div className="text-xs capitalize text-slate-300">{props.type}</div>
                <div className={`text-xs font-medium ${isVerified ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {isVerified ? 'Verified' : 'Unverified'}
                </div>
                <div className="text-xs text-slate-400">{props.source}</div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}

      {/* Site markers */}
      {sites.map((site) => (
        <Marker key={site.site_id} position={[site.lat, site.lon]}>
          <Popup>
            <div className="p-1 space-y-0.5">
              <div className="font-semibold text-slate-100">{site.name}</div>
              <div className="text-xs text-slate-300">
                {site.job_type} &middot; intensity: {site.intensity}
              </div>
            </div>
          </Popup>
        </Marker>
      ))}

      {/* Route lines — green solid for lower exposure, orange dashed for faster */}
      {routes?.map((route) => {
        const isLowerExposure = route.id === 'R01';
        return (
          <Polyline
            key={route.id}
            positions={toLatLngs(route.geometry.coordinates)}
            color={isLowerExposure ? '#4ade80' : '#fb923c'}
            weight={4}
            opacity={0.9}
            dashArray={isLowerExposure ? undefined : '6, 6'}
          />
        );
      })}
    </MapContainer>
  );
}
