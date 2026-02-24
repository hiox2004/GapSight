import { useEffect, useState } from 'react'
import api from '../api/axios'
import MetricCard from '../components/MetricCard'
import FollowerGrowthChart from '../components/FollowerGrowthChart'
import ContentTypePieChart from '../components/ContentTypePieChart'
import PostPerformanceChart from '../components/PostPerformanceChart'
import FrequencyCorrelationChart from '../components/FrequencyCorrelationChart'
import TrendPredictionChart from '../components/TrendPredictionChart'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [followers, setFollowers] = useState([])
  const [contentTypes, setContentTypes] = useState([])
  const [postPerformance, setPostPerformance] = useState([])
  const [frequencyCorrelation, setFrequencyCorrelation] = useState([])
  const [trendPrediction, setTrendPrediction] = useState([])

  const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [summaryRes, followersRes, contentRes, performanceRes, freqRes, trendRes] = await Promise.all([
          api.get('/analytics/summary'),
          api.get('/analytics/followers'),
          api.get('/analytics/content-types'),
          api.get('/analytics/post-performance'),
          api.get('/analytics/frequency-correlation'),
          api.get('/analytics/trend-prediction'),
        ])
        setSummary(summaryRes.data)
        setFollowers(followersRes.data)
        setContentTypes(contentRes.data)
        setPostPerformance(performanceRes.data)
        setFrequencyCorrelation(freqRes.data)
        setTrendPrediction(trendRes.data)
      } catch (err) {
        setError('Failed to load analytics.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [])

  if (loading) return <div className="flex items-center justify-center h-screen text-white text-xl">Loading...</div>
  if (error) return <div className="flex items-center justify-center h-screen text-red-400 text-xl">{error}</div>

  return (
    <div id="dashboard-root" className="p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">Your analytics overview</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <a
          href={`${apiBase}/reports/dashboard.csv`}
          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
        >
          Download CSV report
        </a>
        <a
          href={`${apiBase}/reports/dashboard.pdf`}
          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
        >
          Download dashboard PDF (charts)
        </a>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard title="Followers" value={summary?.follower_count?.toLocaleString() ?? '—'} />
        <MetricCard title="Avg Engagement" value={summary?.avg_engagement ?? '—'} />
        <MetricCard title="Posts / Week" value={summary?.posts_per_week ?? '—'} />
        <MetricCard title="Top Content" value={summary?.top_content_type ?? '—'} />

      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-2xl p-4">
          <h2 className="text-lg font-semibold mb-3 text-white">Follower Growth</h2>
          <FollowerGrowthChart data={followers} />
        </div>
        <div className="bg-gray-900 rounded-2xl p-4">
          <h2 className="text-lg font-semibold mb-3 text-white">Content Breakdown</h2>
          <ContentTypePieChart data={contentTypes} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-2xl p-4">
          <h2 className="text-lg font-semibold mb-3 text-white">Post Performance Over Time</h2>
          <PostPerformanceChart data={postPerformance} />
        </div>
        <div className="bg-gray-900 rounded-2xl p-4">
          <h2 className="text-lg font-semibold mb-3 text-white">Posting Frequency vs Engagement</h2>
          <FrequencyCorrelationChart data={frequencyCorrelation} />
        </div>
      </div>

      <div className="bg-gray-900 rounded-2xl p-4">
        <h2 className="text-lg font-semibold mb-3 text-white">Follower Trend Prediction (Next 4 Weeks)</h2>
        <TrendPredictionChart data={trendPrediction} />
      </div>
    </div>
  )
}
