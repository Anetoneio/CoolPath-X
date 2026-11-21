// Single API config constant. Override via env if needed.
export const API_BASE_URL = 'http://localhost:8000';

export function api(path) {
  return `${API_BASE_URL}${path}`;
}