import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  GeoJSON,
  CircleMarker,
  Polyline,
} from 'react-leaflet';

// Colour ramp for heat_index_0_100 (exposure values are estimates).
function heatColor(index) {
  if (index >= 80) return '#7f0000';
  if (index >= 70) return '#ff4d4d';
  if (index >= 60) return '#ffa64d';
  if (index >= 50) return '#ffe066';
  return '#d9f2a6';
}

function heatStyle(feature) {
  const index = feature.properties?.heat_index_0_100 ?? 50;
  return {
    color: heatColor(index),
    weight: 1,
    fillColor: heatColor(index),
    fillOpacity: 0.5,
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
  const baseColor = isWater ? '#2196F3' : '#4CAF50';
  return {
    radius: 8,
    color: baseColor,
    weight: 2,
    fillColor: baseColor,
    fillOpacity: isVerified ? 0.7 : 0.2,
    dashArray: isVerified ? undefined : '5, 5',
  };
}

export default function MapView({ sites, facilities, heatGrid, heatVisible, routes }) {
  const facilityFeatures = facilities?.features ?? [];

  return (
    <MapContainer center={CENTER} zoom={12} className="absolute inset-0">
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap contributors'
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
              <div className="p-1">
                <div className="font-bold">{props.id}</div>
                <div className="text-xs capitalize">{props.type}</div>
                <div className={`text-xs font-medium ${isVerified ? 'text-green-700' : 'text-orange-600'}`}>
                  {isVerified ? 'Verified' : 'Unverified'}
                </div>
                <div className="text-xs text-slate-500">{props.source}</div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}

      {/* Site markers */}
      {sites.map((site) => (
        <Marker key={site.site_id} position={[site.lat, site.lon]}>
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

      {/* Route lines — green solid for lower exposure, orange dashed for faster */}
      {routes?.map((route) => {
        const isLowerExposure = route.id === 'R01';
        return (
          <Polyline
            key={route.id}
            positions={toLatLngs(route.geometry.coordinates)}
            color={isLowerExposure ? '#22c55e' : '#f97316'}
            weight={4}
            opacity={0.8}
            dashArray={isLowerExposure ? undefined : '6, 6'}
          />
        );
      })}
    </MapContainer>
  );
}