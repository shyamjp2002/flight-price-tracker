import { useState } from 'react'
import type { WatchInput } from '../types'
import { AirportInput } from './AirportInput'

const EMPTY: WatchInput = {
  origin: '',
  destination: '',
  depart_date: '',
  return_date: null,
  adults: 1,
  currency: 'USD',
  target_price: null,
  flex_days: 0,
}

interface Props {
  onCreate: (payload: WatchInput) => Promise<void>
}

export function WatchForm({ onCreate }: Props) {
  const [form, setForm] = useState<WatchInput>(EMPTY)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const update = (patch: Partial<WatchInput>) => {
    setError('')
    setForm((current) => ({ ...current, ...patch }))
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setSaving(true)
    try {
      await onCreate({
        ...form,
        origin: form.origin.toUpperCase(),
        destination: form.destination.toUpperCase(),
        currency: form.currency.toUpperCase(),
        return_date: form.return_date || null,
        target_price: form.target_price ? Number(form.target_price) : null,
      })
      setForm({ ...EMPTY, currency: form.currency, flex_days: form.flex_days })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed to create watch')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="card watch-form" onSubmit={submit}>
      <h2>Track a route</h2>
      <div className="grid">
        <AirportInput
          label="From"
          placeholder="Hyderabad or HYD"
          value={form.origin}
          onChange={(origin) => update({ origin })}
        />
        <AirportInput
          label="To"
          placeholder="Dubai or DXB"
          value={form.destination}
          onChange={(destination) => update({ destination })}
        />
        <label>
          Depart
          <input
            required
            type="date"
            value={form.depart_date}
            onChange={(e) => update({ depart_date: e.target.value })}
          />
        </label>
        <label>
          Return (optional)
          <input
            type="date"
            value={form.return_date ?? ''}
            onChange={(e) => update({ return_date: e.target.value || null })}
          />
        </label>
        <label>
          Adults
          <input
            type="number"
            min={1}
            max={9}
            value={form.adults}
            onChange={(e) => update({ adults: Number(e.target.value) })}
          />
        </label>
        <label>
          Currency
          <input
            maxLength={3}
            value={form.currency}
            onChange={(e) => update({ currency: e.target.value })}
          />
        </label>
        <label>
          Flexible dates
          <select
            value={form.flex_days}
            onChange={(e) => update({ flex_days: Number(e.target.value) })}
          >
            <option value={0}>exact dates</option>
            <option value={1}>± 1 day</option>
            <option value={2}>± 2 days</option>
            <option value={3}>± 3 days</option>
            <option value={7}>± 7 days</option>
          </select>
        </label>
        <label>
          Alert below
          <input
            type="number"
            min={1}
            step="1"
            placeholder="450"
            value={form.target_price ?? ''}
            onChange={(e) =>
              update({ target_price: e.target.value ? Number(e.target.value) : null })
            }
          />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={saving}>
        {saving ? 'Adding…' : 'Add watch'}
      </button>
    </form>
  )
}
