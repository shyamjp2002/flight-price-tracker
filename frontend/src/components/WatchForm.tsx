import { useState } from 'react'
import type { WatchInput } from '../types'

const EMPTY: WatchInput = {
  origin: '',
  destination: '',
  depart_date: '',
  return_date: null,
  adults: 1,
  currency: 'USD',
  target_price: null,
}

interface Props {
  onCreate: (payload: WatchInput) => Promise<void>
}

export function WatchForm({ onCreate }: Props) {
  const [form, setForm] = useState<WatchInput>(EMPTY)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

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
      setForm(EMPTY)
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
        <label>
          From
          <input
            required
            maxLength={3}
            placeholder="HYD"
            value={form.origin}
            onChange={(e) => setForm({ ...form, origin: e.target.value })}
          />
        </label>
        <label>
          To
          <input
            required
            maxLength={3}
            placeholder="DXB"
            value={form.destination}
            onChange={(e) => setForm({ ...form, destination: e.target.value })}
          />
        </label>
        <label>
          Depart
          <input
            required
            type="date"
            value={form.depart_date}
            onChange={(e) => setForm({ ...form, depart_date: e.target.value })}
          />
        </label>
        <label>
          Return (optional)
          <input
            type="date"
            value={form.return_date ?? ''}
            onChange={(e) => setForm({ ...form, return_date: e.target.value || null })}
          />
        </label>
        <label>
          Adults
          <input
            type="number"
            min={1}
            max={9}
            value={form.adults}
            onChange={(e) => setForm({ ...form, adults: Number(e.target.value) })}
          />
        </label>
        <label>
          Currency
          <input
            maxLength={3}
            value={form.currency}
            onChange={(e) => setForm({ ...form, currency: e.target.value })}
          />
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
              setForm({ ...form, target_price: e.target.value ? Number(e.target.value) : null })
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
