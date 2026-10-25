const BASE = import.meta.env.VITE_API_URL || '/api'

export const getToken = () => localStorage.getItem('nx_token')
export const setToken = (t) =>
    t ? localStorage.setItem('nx_token', t) : localStorage.removeItem('nx_token')

export class ApiError extends Error {
    constructor(message, status) {
        super(message)
        this.status = status
    }
}

function errorText(detail, fallback) {
    if (!detail) return fallback
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail))
        return detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ')
    return fallback
}

async function request(path, { method = 'GET', body, form, params } = {}) {
    const url = new URL(BASE + path, window.location.origin)
    Object.entries(params || {}).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
    })
    const headers = {}
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
    let payload
    if (form) {
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        payload = new URLSearchParams(form)
    } else if (body !== undefined) {
        headers['Content-Type'] = 'application/json'
        payload = JSON.stringify(body)
    }
    let res
    try {
        res = await fetch(url, { method, headers, body: payload })
    } catch {
        throw new ApiError('Cannot reach the server. Check that the backend is running.', 0)
    }
    const data = res.status === 204 ? null : await res.json().catch(() => null)
    if (!res.ok) {
        if (res.status === 401 && token) {
            setToken(null)
            window.dispatchEvent(new Event('nx-logout'))
        }
        throw new ApiError(errorText(data?.detail, `Request failed (${res.status})`), res.status)
    }
    return data
}

export const api = {
    get: (p, params) => request(p, { params }),
    post: (p, body) => request(p, { method: 'POST', body }),
    patch: (p, body) => request(p, { method: 'PATCH', body }),
    put: (p, body) => request(p, { method: 'PUT', body }),
    del: (p) => request(p, { method: 'DELETE' }),
    login: (email, password) =>
        request('/auth/login', { method: 'POST', form: { username: email, password } }),
}

export const inr = (n) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(
        Number(n) || 0
    )
export const num = (n) => new Intl.NumberFormat('en-IN').format(Number(n) || 0)

// Store used for POS, inventory and expenses. The backend takes a free-text store_id.
export const getStore = () => localStorage.getItem('nx_store') || 'store-1'
export const setStore = (s) => localStorage.setItem('nx_store', s)
