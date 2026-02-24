import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

const COLORS = ['#6366F1', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6']

export default function CompetitorGrowthChart({ series }) {
  if (!Array.isArray(series) || series.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        No follower history available yet
      </div>
    )
  }

  const dates = new Set()
  series.forEach(line => {
    line.data.forEach(point => {
      dates.add(point.date)
    })
  })

  const sortedDates = Array.from(dates).sort()

  const chartData = sortedDates.map(date => {
    const row = { date }
    series.forEach(line => {
      const match = line.data.find(point => point.date === date)
      if (match) {
        row[line.name] = match.followers
      }
    })
    return row
  })

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
          labelStyle={{ color: '#F9FAFB' }}
        />
        <Legend formatter={value => <span style={{ color: '#D1D5DB' }}>{value}</span>} />
        {series.map((line, index) => (
          <Line
            key={line.name}
            type="monotone"
            dataKey={line.name}
            stroke={COLORS[index % COLORS.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
