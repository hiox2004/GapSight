import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function PostPerformanceChart({ data }) {
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400">
        No post data available
      </div>
    )
  }

  const formatted = data.map(item => ({
    date: item.date,
    engagement: item.engagement,
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={formatted} barCategoryGap="25%">
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
          labelStyle={{ color: '#F9FAFB' }}
          formatter={(value) => [value, 'Total engagement']}
        />
        <Bar dataKey="engagement" name="Total engagement" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
