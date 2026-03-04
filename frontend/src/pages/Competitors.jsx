import { useEffect, useState, useCallback } from 'react'
import api from '../api/axios'
import { useUser } from '../context/UserContext'
import CompetitorFollowersChart from '../components/CompetitorFollowersChart'
import CompetitorEngagementChart from '../components/CompetitorEngagementChart'
import CompetitorGrowthChart from '../components/CompetitorGrowthChart'

export default function Competitors() {
  const { username } = useUser()
  const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

  const [competitorList, setCompetitorList] = useState([])
  const [competitors, setCompetitors] = useState([])
  const [gaps, setGaps] = useState([])
  const [growthSeries, setGrowthSeries] = useState([])
  // initialLoading is true only for the very first fetch — charts stay visible on subsequent refreshes
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState(null)

  const [addInput, setAddInput] = useState('')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState(null)
  const [syncingMsg, setSyncingMsg] = useState('')

  const fetchAll = useCallback(async () => {
    if (!username) return
    setError(null)
    try {
      const params = { username }
      const [listRes, compareRes, gapsRes, growthRes] = await Promise.all([
        api.get('/competitors/list', { params }),
        api.get('/competitors/compare', { params }),
        api.get('/competitors/gaps', { params }),
        api.get('/competitors/growth', { params }),
      ])
      setCompetitorList(listRes.data || [])
      setCompetitors(compareRes.data || [])
      setGaps(gapsRes.data || [])
      setGrowthSeries(growthRes.data || [])
    } catch (err) {
      setError('Failed to load competitor data.')
      console.error(err)
    } finally {
      setInitialLoading(false)
    }
  }, [username])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  const handleAdd = async () => {
    const comp = addInput.trim()
    if (!comp || !username) return
    setAdding(true)
    setAddError(null)
    setSyncingMsg('')
    try {
      await api.post('/competitors/', {
        owner_username: username,
        competitor_username: comp,
      })
      setAddInput('')
      // Sync the new competitor so their data is immediately available in charts
      setSyncingMsg(`Syncing @${comp}…`)
      try {
        await api.post(`/sync/${comp}`)
      } catch {
        // Sync failure is non-fatal — competitor is still saved
      }
      setSyncingMsg('')
      await fetchAll()
    } catch (err) {
      setAddError(err?.response?.data?.detail || err?.response?.data?.error || 'Failed to add competitor.')
    } finally {
      setAdding(false)
      setSyncingMsg('')
    }
  }

  const [resyncing, setResyncing] = useState({})

  const handleRemove = async (competitorUsername) => {
    try {
      await api.delete(`/competitors/${competitorUsername}`, { params: { owner_username: username } })
      await fetchAll()
    } catch (err) {
      console.error(err)
    }
  }

  const handleResync = async (competitorUsername) => {
    setResyncing(prev => ({ ...prev, [competitorUsername]: true }))
    try {
      await api.post(`/sync/${competitorUsername}`)
      await fetchAll()
    } catch (err) {
      console.error('Resync failed:', err)
    } finally {
      setResyncing(prev => ({ ...prev, [competitorUsername]: false }))
    }
  }

  const showCompetitors = Array.isArray(competitors) && competitors.length > 0
  const showGaps = Array.isArray(gaps) && gaps.length > 0
  const showGrowth = Array.isArray(growthSeries) && growthSeries.length > 0

  return (
    <div id="competitors-root" className="p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Competitors</h1>
        <p className="text-gray-400 mt-1">See how you stack up</p>
      </div>

      {!username && (
        <div className="flex items-center justify-center h-32 text-gray-500">
          Set your username on the Dashboard first.
        </div>
      )}

      {username && (
        <>
          {/* Manage competitors */}
          <div className="bg-gray-900 rounded-2xl p-4 space-y-4">
            <h2 className="text-lg font-semibold text-white">Manage Competitors</h2>

            {/* Add */}
            <div className="flex gap-2 items-center">
              <input
                type="text"
                value={addInput}
                onChange={(e) => setAddInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
                placeholder="Competitor username"
                className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 w-48 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={handleAdd}
                disabled={adding || !!syncingMsg}
                className="px-3 py-2 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50"
              >
                {syncingMsg ? 'Syncing…' : adding ? 'Adding…' : 'Add'}
              </button>
              {addError && <span className="text-red-400 text-sm">{addError}</span>}
              {syncingMsg && <span className="text-indigo-400 text-sm animate-pulse">{syncingMsg}</span>}
            </div>

            {/* Current list */}
            {competitorList.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {competitorList.map((c) => {
                  const name = c.competitor_username || c.username || String(c.competitor_user_id)
                  return (
                    <div
                      key={c.id}
                      className="flex items-center gap-1.5 bg-gray-800 border border-gray-700 rounded-full px-3 py-1 text-sm text-white"
                    >
                      <span>@{name}</span>
                      <button
                        onClick={() => handleResync(name)}
                        disabled={resyncing[name]}
                        title="Re-sync data from RapidAPI"
                        className="text-gray-400 hover:text-indigo-400 leading-none text-xs disabled:opacity-40"
                      >
                        {resyncing[name] ? '…' : '↻'}
                      </button>
                      <button
                        onClick={() => handleRemove(name)}
                        className="text-gray-400 hover:text-red-400 leading-none text-base"
                      >
                        ×
                      </button>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No competitors added yet.</p>
            )}
          </div>

          {error && <div className="text-red-400 text-sm">{error}</div>}
          {initialLoading && <div className="text-white text-center py-8">Loading…</div>}

          {!initialLoading && (
            <>
              {/* Charts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gray-900 rounded-2xl p-4">
                  <h2 className="text-lg font-semibold mb-3 text-white">Follower Comparison</h2>
                  {showCompetitors ? (
                    <CompetitorFollowersChart data={competitors} />
                  ) : (
                    <div className="flex items-center justify-center h-64 text-gray-400">No data</div>
                  )}
                </div>
                <div className="bg-gray-900 rounded-2xl p-4">
                  <h2 className="text-lg font-semibold mb-3 text-white">Engagement Comparison</h2>
                  {showCompetitors ? (
                    <CompetitorEngagementChart data={competitors} />
                  ) : (
                    <div className="flex items-center justify-center h-64 text-gray-400">No data</div>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <a
                  href={`${apiBase}/reports/competitors.csv?username=${username}`}
                  className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
                >
                  Download competitors CSV
                </a>
                <a
                  href={`${apiBase}/reports/competitors.pdf?username=${username}`}
                  className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
                >
                  Download competitors PDF
                </a>
              </div>

              <div className="bg-gray-900 rounded-2xl p-4">
                <h2 className="text-lg font-semibold mb-3 text-white">Follower Growth Over Time</h2>
                {showGrowth ? (
                  <CompetitorGrowthChart series={growthSeries} />
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-400">No follower history yet</div>
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
                          <th className="py-2">Engagement Gap %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {gaps.map((g, i) => (
                          <tr key={i} className="border-b border-gray-800 hover:bg-gray-800 transition">
                            <td className="py-3 pr-4 font-medium text-white">{g.competitor}</td>
                            <td className="py-3 pr-4">{g.top_content_type}</td>
                            <td className="py-3 pr-4">{g.my_usage ?? 'Low'}</td>
                            <td className="py-3">
                              <span className={`px-2 py-0.5 rounded-full text-xs ${g.gap_score > 0 ? 'bg-red-500/20 text-red-300' : 'bg-emerald-500/20 text-emerald-300'}`}>
                                {g.gap_score > 0 ? `+${g.gap_score}%` : `${g.gap_score}%`}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400">No content gaps data available</div>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
