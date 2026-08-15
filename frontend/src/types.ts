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
}

export interface PricePoint {
  price: number
  currency: string
  carrier: string | null
  deep_link: string | null
  checked_at: string
}

export interface Alert {
  id: number
  watch_id: number
  price: number
  currency: string
  message: string
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
}

export interface CheckResult {
  watch_id: number
  price: number
  currency: string
  carrier: string | null
  deep_link: string | null
  alerted: boolean
  message: string
}
