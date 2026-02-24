import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function CompetitorFollowersChart({ data }) {
  const formatted = data.map(d => ({
    name: d.username,
    followers: d.follower_count,
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={formatted} barCategoryGap="30%">
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="name" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <Tooltip
          formatter={(value) => [value.toLocaleString(), 'Followers']}
          contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
          labelStyle={{ color: '#F9FAFB' }}
        />
        <Bar dataKey="followers" name="Followers" fill="#6366F1" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
