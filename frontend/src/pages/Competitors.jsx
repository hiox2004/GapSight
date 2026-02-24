import { useEffect, useState } from 'react'
import api from '../api/axios'
import CompetitorFollowersChart from '../components/CompetitorFollowersChart'
import CompetitorEngagementChart from '../components/CompetitorEngagementChart'
import CompetitorGrowthChart from '../components/CompetitorGrowthChart'

export default function Competitors() {
  const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
  const [competitors, setCompetitors] = useState([])
  const [gaps, setGaps] = useState([])
  const [growthSeries, setGrowthSeries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [compareRes, gapsRes, growthRes] = await Promise.all([
          api.get('/competitors/compare'),
          api.get('/competitors/gaps'),
          api.get('/competitors/growth'),
        ])
        setCompetitors(compareRes.data)
        setGaps(gapsRes.data)
        setGrowthSeries(growthRes.data)
      } catch (err) {
        setError('Failed to load competitor data.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [])

  if (loading) return <div className="flex items-center justify-center h-screen text-white text-xl">Loading...</div>
  if (error) return <div className="flex items-center justify-center h-screen text-red-400 text-xl">{error}</div>

  const showCompetitors = Array.isArray(competitors) && competitors.length > 0
  const showGaps = Array.isArray(gaps) && gaps.length > 0
  const showGrowth = Array.isArray(growthSeries) && growthSeries.length > 0

  return (
    <div id="competitors-root" className="p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Competitors</h1>
        <p className="text-gray-400 mt-1">See how you stack up</p>
      </div>

      {/* Followers vs Engagement Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-2xl p-4">
          <h2 className="text-lg font-semibold mb-3 text-white">Follower Comparison</h2>
          {showCompetitors ? (
            <CompetitorFollowersChart data={competitors} />
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No competitor data available
            </div>
          )}
        </div>

        <div className="bg-gray-900 rounded-2xl p-4">
          <h2 className="text-lg font-semibold mb-3 text-white">Engagement Comparison</h2>
          {showCompetitors ? (
            <CompetitorEngagementChart data={competitors} />
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No competitor data available
            </div>
          )}
        </div>
      </div>

      {/* Growth Over Time */}
      <div className="flex flex-wrap gap-2">
        <a
          href={`${apiBase}/reports/competitors.csv`}
          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
        >
          Download competitors CSV
        </a>
        <a
          href={`${apiBase}/reports/competitors.pdf`}
          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
        >
          Download competitors PDF (charts)
        </a>
      </div>
      <div className="bg-gray-900 rounded-2xl p-4">
        <h2 className="text-lg font-semibold mb-3 text-white">Follower Growth Over Time</h2>
        {showGrowth ? (
          <CompetitorGrowthChart series={growthSeries} />
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-400">
            No follower history available yet
          </div>
        )}
      </div>

      {/* Gaps Table */}
      <div className="bg-gray-900 rounded-2xl p-4">
        <h2 className="text-lg font-semibold mb-4 text-white">Content Gaps</h2>
        {showGaps ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-gray-300">
              <thead className="text-xs text-gray-400 uppercase border-b border-gray-700">
                <tr>
                  <th className="py-2 pr-4">Competitor</th>
                  <th className="py-2 pr-4">Their Top Content</th>
                  <th className="py-2 pr-4">Your Usage</th>
                  <th className="py-2">Gap</th>
                </tr>
              </thead>
              <tbody>
                {gaps.map((g, i) => (
                  <tr key={i} className="border-b border-gray-800 hover:bg-gray-800 transition">
                    <td className="py-3 pr-4 font-medium text-white">{g.competitor}</td>
                    <td className="py-3 pr-4">{g.their_top_content}</td>
                    <td className="py-3 pr-4">{g.your_usage ?? 'Low'}</td>
                    <td className="py-3">
                      <span className="bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full text-xs">
                        {g.gap}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            No content gaps data available
          </div>
        )}
      </div>
    </div>
  )
}
