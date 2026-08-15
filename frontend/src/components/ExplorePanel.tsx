import { useState } from 'react'
import { api } from '../api'
import type { DestinationDeal } from '../types'
import { AirportInput } from './AirportInput'

export function ExplorePanel() {
  const [origin, setOrigin] = useState('')
  const [departDate, setDepartDate] = useState('')
  const [currency, setCurrency] = useState('USD')
  const [maxPrice, setMaxPrice] = useState('')
  const [deals, setDeals] = useState<DestinationDeal[] | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const search = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      setDeals(
        await api.explore(
          origin.toUpperCase(),
          departDate,
          currency.toUpperCase(),
          maxPrice ? Number(maxPrice) : null,
        ),
      )
    } catch (err) {
      setDeals(null)
      setError(err instanceof Error ? err.message : 'search failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <h2>Go anywhere</h2>
      <p className="muted">Cheapest destinations from one airport, when the where is up to you.</p>
      <form className="grid" onSubmit={search}>
        <AirportInput
          label="From"
          placeholder="Hyderabad or HYD"
          value={origin}
          onChange={setOrigin}
        />
        <label>
          Depart
          <input
            required
            type="date"
            value={departDate}
            onChange={(e) => setDepartDate(e.target.value)}
          />
        </label>
        <label>
          Currency
          <input maxLength={3} value={currency} onChange={(e) => setCurrency(e.target.value)} />
        </label>
        <label>
          Max price
          <input
            type="number"
            min={1}
            placeholder="300"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? 'Searching…' : 'Find deals'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {deals !== null && deals.length === 0 && <p className="muted">No destinations found.</p>}
      {deals !== null && deals.length > 0 && (
        <ul className="deals">
          {deals.map((deal) => (
            <li key={`${deal.destination}-${deal.depart_date}`}>
              <span>
                <strong>{deal.destination_label || deal.destination}</strong> · {deal.depart_date}
                {deal.return_date ? ` – ${deal.return_date}` : ''}
              </span>
              <span>
                {deal.currency} {deal.price.toFixed(0)}
                {deal.deep_link && (
                  <a href={deal.deep_link} target="_blank" rel="noreferrer">
                    book
                  </a>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
