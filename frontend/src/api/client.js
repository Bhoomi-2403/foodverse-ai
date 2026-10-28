import axios from 'axios';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const http = axios.create({ baseURL: API_BASE, timeout: 120000 });

/** Turn any Axios error into a readable message. */
export function errorMessage(err) {
  if (err?.response) {
    const d = err.response.data?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map((x) => `${(x.loc || []).slice(1).join('.')}: ${x.msg}`).join('; ');
    return `Request failed (HTTP ${err.response.status}).`;
  }
  if (err?.code === 'ECONNABORTED') return 'The request timed out. Please try again.';
  if (err?.request) return `Cannot reach the backend at ${API_BASE}. Is it running?`;
  return err?.message || 'Unexpected error.';
}

/** Build FormData skipping empty values. Do NOT set Content-Type manually: the browser adds the boundary. */
export function toFormData(fields) {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return;
    if (v instanceof Blob && !(v instanceof File)) fd.append(k, v, `${k}.webm`);
    else fd.append(k, v);
  });
  return fd;
}

const post = (url, fields, config) => http.post(url, toFormData(fields), config).then((r) => r.data);

export const api = {
  health: () => http.get('/health').then((r) => r.data),
  analyzeFood: (f) => post('/api/food-recognition/analyze', f),
  analyzeFreshness: (f) => post('/api/freshness-detector/analyze', f),
  analyzeHygiene: (f) => post('/api/hygiene-monitor/analyze', f),
  hygieneReport: (result) =>
    http.post('/api/hygiene-monitor/report', { result }, { responseType: 'blob' }).then((r) => r.data),
  generateRecipe: (f) => post('/api/kitchen-assistant/generate-recipe', f),
  generatePlan: (f) => post('/api/meal-planner/generate', f),
};
