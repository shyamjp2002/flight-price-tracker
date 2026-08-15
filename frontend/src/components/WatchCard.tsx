import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { PricePoint, Watch } from '../types'
import { PriceChart } from './PriceChart'

interface Props {
  watch: Watch
  onChanged: () => Promise<void>
}

const VERDICTS: Record<string, string> = {
  buy: 'Buy now',
  wait: 'Wait',
  watch: 'Keep watching',
}

function money(value: number | null, currency: string) {
  return value === null ? '—' : `${currency} ${value.toFixed(2)}`
}

export function WatchCard({ watch, onChanged }: Props) {
  const [points, setPoints] = useState<PricePoint[]>([])
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')

  const loadHistory = useCallback(async () => {
    setPoints(await api.prices(watch.id))
  }, [watch.id])

  useEffect(() => {
    if (open) {
      void loadHistory()
    }
  }, [open, loadHistory, watch.checks])

  const toggleHistory = () => {
    setOpen(!open)
  }

  const checkNow = async () => {
    setBusy(true)
    setNote('')
    try {
      const result = await api.checkWatch(watch.id)
      const forDate = result.for_date === watch.depart_date ? '' : ` on ${result.for_date}`
      setNote(result.message || `Now ${money(result.price, result.currency)}${forDate}`)
      await onChanged()
    } catch (err) {
      setNote(err instanceof Error ? err.message : 'check failed')
    } finally {
      setBusy(false)
    }
  }

  const remove = async () => {
    await api.deleteWatch(watch.id)
    await onChanged()
  }

  const togglePaused = async () => {
    await api.toggleWatch(watch.id, !watch.active)
    await onChanged()
  }

  const cheapestDate = points.length ? points[points.length - 1].for_date : null

  const isDeal =
    watch.target_price !== null &&
    watch.latest_price !== null &&
    watch.latest_price <= watch.target_price

  return (
    <article className={`card watch ${watch.active ? '' : 'paused'}`}>
      <header>
        <h3>
          {watch.origin_label || watch.origin} → {watch.destination_label || watch.destination}
        </h3>
        <span className="muted">
          {watch.depart_date}
          {watch.return_date ? ` – ${watch.return_date}` : ''} · {watch.adults} adult
          {watch.adults > 1 ? 's' : ''}
          {watch.flex_days > 0 ? ` · ±${watch.flex_days}d flexible` : ''}
        </span>
      </header>

      <dl className="stats">
        <div>
          <dt>Latest</dt>
          <dd className={isDeal ? 'deal' : ''}>{money(watch.latest_price, watch.currency)}</dd>
        </div>
        <div>
          <dt>Lowest seen</dt>
          <dd>{money(watch.lowest_price, watch.currency)}</dd>
        </div>
        <div>
          <dt>Target</dt>
          <dd>{money(watch.target_price, watch.currency)}</dd>
        </div>
        <div>
          <dt>Checks</dt>
          <dd>{watch.checks}</dd>
        </div>
      </dl>

      {watch.recommendation && (
        <p className={`verdict ${watch.recommendation.verdict}`}>
          <strong>{VERDICTS[watch.recommendation.verdict]}</strong> {watch.recommendation.reason}
        </p>
      )}

      {cheapestDate && cheapestDate !== watch.depart_date && (
        <p className="muted">Cheapest date found: {cheapestDate}</p>
      )}

      {note && <p className="note">{note}</p>}

      <footer>
        <button onClick={checkNow} disabled={busy}>
          {busy ? 'Checking…' : 'Check now'}
        </button>
        <button className="secondary" onClick={toggleHistory}>
          {open ? 'Hide history' : 'History'}
        </button>
        <button className="secondary" onClick={togglePaused}>
          {watch.active ? 'Pause' : 'Resume'}
        </button>
        <button className="danger" onClick={remove}>
          Delete
        </button>
      </footer>

      {open && <PriceChart points={points} target={watch.target_price} />}
    </article>
  )
}
