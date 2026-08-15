export interface Watch {
  id: number
  origin: string
  destination: string
  depart_date: string
  return_date: string | null
  adults: number
  currency: string
  target_price: number | null
  active: boolean
  created_at: string
  latest_price: number | null
  lowest_price: number | null
  checks: number
  flex_days: number
  origin_label: string
  destination_label: string
  recommendation: Recommendation | null
}

export interface Recommendation {
  verdict: 'buy' | 'wait' | 'watch'
  reason: string
  latest_price: number | null
  lowest_price: number | null
  average_price: number | null
  percent_vs_average: number | null
  trend: string
  days_to_departure: number | null
}

export interface Airport {
  iata: string
  name: string
  city: string
  country: string
}

export interface DestinationDeal {
  destination: string
  destination_label: string
  price: number
  currency: string
  depart_date: string
  return_date: string | null
  deep_link: string | null
}

export interface PricePoint {
  price: number
  currency: string
  carrier: string | null
  deep_link: string | null
  for_date: string | null
  checked_at: string
}

export interface Alert {
  id: number
  watch_id: number
  price: number
  currency: string
  message: string
  delivered_to: string
  created_at: string
}

export interface WatchInput {
  origin: string
  destination: string
  depart_date: string
  return_date: string | null
  adults: number
  currency: string
  target_price: number | null
  flex_days: number
}

export interface CheckResult {
  watch_id: number
  price: number
  currency: string
  carrier: string | null
  deep_link: string | null
  for_date: string
  alerted: boolean
  message: string
}
