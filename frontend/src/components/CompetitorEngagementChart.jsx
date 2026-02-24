import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function CompetitorEngagementChart({ data }) {
  const formatted = data.map(d => ({
    name: d.username,
    engagement: d.avg_engagement,
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={formatted} barCategoryGap="30%">
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="name" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <Tooltip
          formatter={(value) => [value, 'Avg Engagement']}
          contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
          labelStyle={{ color: '#F9FAFB' }}
        />
        <Bar dataKey="engagement" name="Avg Engagement" fill="#10B981" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
