import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { PricePoint } from '../types'

interface Props {
  points: PricePoint[]
  target: number | null
}

export function PriceChart({ points, target }: Props) {
  if (points.length === 0) {
    return <p className="muted">No price checks yet — run “Check now”.</p>
  }

  const data = points.map((point) => ({
    label: point.checked_at.slice(5, 16),
    price: point.price,
    target,
  }))

  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid stroke="#26314a" strokeDasharray="3 3" />
          <XAxis dataKey="label" stroke="#8b9bb8" fontSize={11} />
          <YAxis stroke="#8b9bb8" fontSize={11} domain={['auto', 'auto']} />
          <Tooltip
            contentStyle={{ background: '#131a2a', border: '1px solid #26314a', borderRadius: 8 }}
          />
          <Line type="monotone" dataKey="price" stroke="#4da3ff" strokeWidth={2} dot={false} />
          {target !== null && (
            <Line
              type="monotone"
              dataKey="target"
              stroke="#f0a13a"
              strokeDasharray="5 5"
              strokeWidth={1.5}
              dot={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
