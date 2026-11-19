const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim()
const apiBaseUrl = configuredBaseUrl.replace(/\/+$/, '')

export function apiUrl(path) {
  return `${apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`
}

export function apiFetch(path, options = {}) {
  return fetch(apiUrl(path), { ...options, credentials: 'include' })
}
