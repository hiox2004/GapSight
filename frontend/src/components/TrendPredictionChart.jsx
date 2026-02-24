import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function TrendPredictionChart({ data }) {
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400">
        Not enough data to predict the trend yet
      </div>
    )
  }

  const formatted = data.map(item => ({
    date: item.date,
    actual: item.type === 'actual' ? item.followers : null,
    predicted: item.type === 'predicted' ? item.followers : null,
  }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={formatted}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
          labelStyle={{ color: '#F9FAFB' }}
        />
        <Line
          type="monotone"
          dataKey="actual"
          name="Actual"
          stroke="#6366F1"
          strokeWidth={2}
          dot={false}
          connectNulls={false}
        />
        <Line
          type="monotone"
          dataKey="predicted"
          name="Predicted"
          stroke="#F59E0B"
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={false}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
