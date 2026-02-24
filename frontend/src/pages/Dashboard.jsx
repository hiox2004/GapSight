import MetricCard from '../components/MetricCard'
import { Users, TrendingUp, FileText, Calendar } from 'lucide-react'

export default function Dashboard() {
  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard title="Total Followers" value="24,500" subtitle="+12% this month" icon={<Users size={16} />} />
        <MetricCard title="Engagement Rate" value="4.8%" subtitle="+0.3% this week" icon={<TrendingUp size={16} />} />
        <MetricCard title="Top Content" value="Reels" subtitle="38% of total engagement" icon={<FileText size={16} />} />
        <MetricCard title="Posts This Week" value="5" subtitle="Avg 4.2 last month" icon={<Calendar size={16} />} />
      </div>
    </div>
  )
}
