import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer
} from 'recharts'

const COLORS = ['#6366F1', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981']

export default function ContentTypePieChart({ data }) {
  const formatted = data.map(d => ({
    name: d.content_type,
    value: d.count
  }))

  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={formatted}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={4}
          dataKey="value"
        >
          {formatted.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
          labelStyle={{ color: '#F9FAFB' }}
        />
        <Legend
          formatter={(value) => <span style={{ color: '#D1D5DB' }}>{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
