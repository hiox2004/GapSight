import { useEffect, useState, useCallback } from 'react'
import api from '../api/axios'
import { useUser } from '../context/UserContext'
import MetricCard from '../components/MetricCard'
import FollowerGrowthChart from '../components/FollowerGrowthChart'
import ContentTypePieChart from '../components/ContentTypePieChart'
import PostPerformanceChart from '../components/PostPerformanceChart'
import FrequencyCorrelationChart from '../components/FrequencyCorrelationChart'
import TrendPredictionChart from '../components/TrendPredictionChart'

export default function Dashboard() {
  const { username, setUsername } = useUser()
  const [inputVal, setInputVal] = useState(username)
  const [summary, setSummary] = useState(null)
  const [followers, setFollowers] = useState([])
  const [contentTypes, setContentTypes] = useState([])
  const [postPerformance, setPostPerformance] = useState([])
  const [frequencyCorrelation, setFrequencyCorrelation] = useState([])
  const [trendPrediction, setTrendPrediction] = useState([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [fetchingHistory, setFetchingHistory] = useState(false)
  const [error, setError] = useState(null)

  const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

  const fetchAnalytics = useCallback(async (user) => {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      const params = { username: user }
      const [summaryRes, followersRes, contentRes, performanceRes, freqRes, trendRes] =
        await Promise.allSettled([
          api.get('/analytics/summary', { params }),
          api.get('/analytics/followers', { params }),
          api.get('/analytics/content-types', { params }),
          api.get('/analytics/post-performance', { params }),
          api.get('/analytics/frequency-correlation', { params }),
          api.get('/analytics/trend-prediction', { params }),
        ])

      if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value.data)
      if (followersRes.status === 'fulfilled') setFollowers(followersRes.value.data)
      if (contentRes.status === 'fulfilled') setContentTypes(contentRes.value.data)
      if (performanceRes.status === 'fulfilled') setPostPerformance(performanceRes.value.data)
      if (freqRes.status === 'fulfilled') setFrequencyCorrelation(freqRes.value.data)
      if (trendRes.status === 'fulfilled') setTrendPrediction(trendRes.value.data)

      const anyFailed = [summaryRes, followersRes, contentRes, performanceRes, freqRes, trendRes]
        .some(r => r.status === 'rejected')
      if (anyFailed) {
        const allFailed = [summaryRes, followersRes, contentRes, performanceRes, freqRes, trendRes]
          .every(r => r.status === 'rejected')
        setError(allFailed ? 'Failed to load analytics.' : 'Some analytics sections failed to load.')
      }
    } catch (err) {
      setError('Failed to load analytics.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (username) fetchAnalytics(username)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSync = async () => {
    const user = inputVal.trim()
    if (!user) return
    setSyncing(true)
    setError(null)
    try {
      await api.post(`/sync/${user}`)
      setUsername(user)
      await fetchAnalytics(user)
    } catch (err) {
      setError('Sync failed. Check the username and try again.')
      console.error(err)
    } finally {
      setSyncing(false)
    }
  }

  const handleFetchHistory = async () => {
    const user = inputVal.trim() || username
    if (!user) return
    setFetchingHistory(true)
    setError(null)
    try {
      await api.post(`/sync/${user}?fetch_history=true`)
      // Apify runs in the background — notify user to reload in a few minutes
      setError('History fetch started. Apify is running in the background (2–5 min). Click Load when done.')
    } catch (err) {
      setError('Failed to start history fetch. Check uvicorn logs for details.')
      console.error(err)
    } finally {
      setFetchingHistory(false)
    }
  }

  const handleLoad = async () => {
    const user = inputVal.trim()
    if (!user) return
    setUsername(user)
    await fetchAnalytics(user)
  }

  return (
    <div id="dashboard-root" className="p-6 space-y-8">
      {/* Header + username switcher */}
      <div className="flex flex-col md:flex-row md:items-end gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 mt-1">Your analytics overview</p>
        </div>
        <div className="flex gap-2 md:ml-auto items-center">
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleLoad()}
            placeholder="Instagram username"
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 w-48 focus:outline-none focus:border-indigo-500"
          />
          <button
            onClick={handleLoad}
            disabled={loading || syncing}
            className="px-3 py-2 text-sm rounded-lg bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-50"
          >
            Load
          </button>
          <button
            onClick={handleSync}
            disabled={syncing || loading || fetchingHistory}
            className="px-3 py-2 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {syncing ? 'Syncing…' : 'Sync'}
          </button>
          <button
            onClick={handleFetchHistory}
            disabled={syncing || loading || fetchingHistory}
            title="Re-fetch full follower history via Apify (requires APIFY_API_TOKEN)"
            className="px-3 py-2 text-sm rounded-lg bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-50"
          >
            {fetchingHistory ? 'Fetching…' : 'Fetch History'}
          </button>
        </div>
      </div>

      {error && <div className="text-red-400 text-sm">{error}</div>}

      {!username && !loading && (
        <div className="flex items-center justify-center h-64 text-gray-500">
          Enter an Instagram username and click Sync (fetches fresh data) or Load (reads saved data).
        </div>
      )}

      {loading && <div className="flex items-center justify-center h-64 text-white text-xl">Loading…</div>}

      {!loading && username && summary && (
        <>
          <div className="flex flex-wrap gap-2">
            <a
              href={`${apiBase}/reports/dashboard.csv?username=${username}`}
              className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
            >
              Download CSV report
            </a>
            <a
              href={`${apiBase}/reports/dashboard.pdf?username=${username}`}
              className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
            >
              Download dashboard PDF
            </a>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <MetricCard title="Followers" value={summary?.follower_count?.toLocaleString() ?? '—'} />
            <MetricCard title="Avg Engagement" value={summary?.avg_engagement ?? '—'} />
            <MetricCard title="Posts / Week" value={summary?.posts_per_week ?? '—'} />
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
        </>
      )}
    </div>
  )
}
