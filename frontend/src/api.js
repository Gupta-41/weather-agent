const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError("Can't reach the agent. Is the backend running?", 0);
  }

  if (response.status === 204) return null;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(body?.detail || `Request failed (${response.status})`, response.status);
  }
  return body;
}

const query = (params) =>
  new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null)
  ).toString();

export const api = {
  health: () => request("/api/health"),
  tools: () => request("/api/tools"),
  languages: () => request("/api/languages"),

  chat: (message, history, language) =>
    request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, history, language }),
    }),

  locations: () => request("/api/locations"),
  saveLocation: (location, language) =>
    request("/api/locations", {
      method: "POST",
      body: JSON.stringify({ location, language }),
    }),
  deleteLocation: (id) => request(`/api/locations/${id}`, { method: "DELETE" }),

  alerts: (language, unacknowledgedOnly = false) =>
    request(`/api/alerts?${query({ language, unacknowledged_only: unacknowledgedOnly })}`),
  refreshAlerts: () => request("/api/alerts/refresh", { method: "POST" }),
  acknowledgeAlert: (id) => request(`/api/alerts/${id}/ack`, { method: "POST" }),
};

export { ApiError };
