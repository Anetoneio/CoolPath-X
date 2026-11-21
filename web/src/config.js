// Single API client file. All fetch calls go through this file.
// API_BASE_URL is the single base-URL constant; no other file defines a URL.
// The engine serves mock endpoints at this base URL until the real engine is ready.
// All heat and exposure values from the engine are estimates — label them "(estimate)" in UI.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function api(path) {
  return `${API_BASE_URL}${path}`;
}

async function _json(res) {
  if (!res.ok) {
    throw new Error(`API ${res.url} returned ${res.status}`);
  }
  return res.json();
}

export async function getSites() {
  const res = await fetch(api('/sites'));
  return _json(res);
}

export async function getFacilities() {
  const res = await fetch(api('/facilities'));
  return _json(res);
}

export async function getHeatGrid() {
  const res = await fetch(api('/heat-grid'));
  return _json(res);
}

export async function getConfidence() {
  const res = await fetch(api('/confidence'));
  return _json(res);
}

export async function postSchedule(body) {
  const res = await fetch(api('/schedule'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return _json(res);
}

export async function postRouteCompare(body) {
  const res = await fetch(api('/route/compare'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return _json(res);
}

// Stretch: only add postSimulate to config.js. Do not build /simulate UI until C2 checkpoint is confirmed.
export async function postSimulate(body) {
  const res = await fetch(api('/simulate'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return _json(res);
}