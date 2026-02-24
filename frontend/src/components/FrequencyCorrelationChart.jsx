import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function FrequencyCorrelationChart({ data }) {
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400">
        Not enough data to show the correlation yet
      </div>
    )
  }

  const formatted = data.map(item => ({
    label: item.week,
    posts: item.post_count,
    engagement: item.avg_engagement,
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          type="number"
          dataKey="posts"
          name="Posts per week"
          stroke="#9CA3AF"
          tick={{ fontSize: 12 }}
        />
        <YAxis
          type="number"
          dataKey="engagement"
          name="Avg engagement"
          stroke="#9CA3AF"
          tick={{ fontSize: 12 }}
        />
        <Tooltip
          cursor={{ strokeDasharray: '3 3' }}
          contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
          labelStyle={{ color: '#F9FAFB' }}
          formatter={(value, name, props) => {
            if (name === 'posts') {
              return [value, 'Posts per week']
            }
            if (name === 'engagement') {
              return [value, 'Avg engagement']
            }
            return [value, name]
          }}
          labelFormatter={(_, payload) => {
            if (payload && payload[0]) {
              return `Week ${payload[0].payload.label}`
            }
            return ''
          }}
        />
        <Scatter data={formatted} fill="#F59E0B" />
      </ScatterChart>
    </ResponsiveContainer>
  )
}
