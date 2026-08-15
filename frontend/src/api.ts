import type {
  Airport,
  Alert,
  CheckResult,
  DestinationDeal,
  PricePoint,
  Watch,
  WatchInput,
} from './types'

interface ValidationIssue {
  loc: (string | number)[]
  msg: string
}

function readableError(body: string, response: Response): string {
  try {
    const detail = (JSON.parse(body) as { detail?: string | ValidationIssue[] }).detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      return detail
        .map((issue) => {
          const field = issue.loc.filter((part) => part !== 'body').join('.')
          const message = issue.msg.replace(/^Value error, /, '')
          return field ? `${field}: ${message}` : message
        })
        .join('; ')
    }
  } catch {
    // not a JSON error payload — fall through to the raw body
  }
  return body || `${response.status} ${response.statusText}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    throw new Error(readableError(await response.text(), response))
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export const api = {
  listWatches: () => request<Watch[]>('/api/watches'),
  createWatch: (payload: WatchInput) =>
    request<Watch>('/api/watches', { method: 'POST', body: JSON.stringify(payload) }),
  deleteWatch: (id: number) => request<void>(`/api/watches/${id}`, { method: 'DELETE' }),
  toggleWatch: (id: number, active: boolean) =>
    request<Watch>(`/api/watches/${id}/active?active=${active}`, { method: 'POST' }),
  prices: (id: number) => request<PricePoint[]>(`/api/watches/${id}/prices`),
  checkWatch: (id: number) => request<CheckResult>(`/api/watches/${id}/check`, { method: 'POST' }),
  checkAll: () => request<{ checked: number }>('/api/check-all', { method: 'POST' }),
  alerts: () => request<Alert[]>('/api/alerts'),
  airports: (query: string) =>
    request<Airport[]>(`/api/airports?q=${encodeURIComponent(query)}`),
  explore: (origin: string, departDate: string, currency: string, maxPrice: number | null) => {
    const params = new URLSearchParams({
      origin,
      depart_date: departDate,
      currency,
    })
    if (maxPrice) {
      params.set('max_price', String(maxPrice))
    }
    return request<DestinationDeal[]>(`/api/explore?${params}`)
  },
  digest: () => request<{ body: string; enabled: boolean }>('/api/digest'),
  sendDigest: () => request<{ delivered_to: string[] }>('/api/digest/send', { method: 'POST' }),
}
