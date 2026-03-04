import { useEffect, useState, useCallback } from 'react'
import api from '../api/axios'
import { useUser } from '../context/UserContext'
import InsightsPanel from '../components/InsightsPanel'

export default function Insights() {
  const { username } = useUser()
  const [insights, setInsights] = useState(null)
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

  const fetchInsights = useCallback(async () => {
    if (!username) return
    setLoading(true)
    setError(null)

    try {
      const params = { username }
      const [res, workflowsRes] = await Promise.allSettled([
        api.get('/insights/', { params }),
        api.get('/insights/workflows', { params }),
      ])

      if (res.status === 'fulfilled') {
        setInsights(res.value.data)
      } else {
        setError('Failed to load insights. Please check backend/API key setup and retry.')
        return
      }

      if (workflowsRes.status === 'fulfilled' && Array.isArray(workflowsRes.value.data)) {
        setWorkflows(workflowsRes.value.data)
      } else {
        setWorkflows([])
      }
    } catch (err) {
      setError('Failed to load insights. Please check backend/API key setup and retry.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [username])

  useEffect(() => {
    fetchInsights()
  }, [fetchInsights])

  if (!username) return (
    <div className="flex items-center justify-center h-screen text-gray-500">
      Set your username on the Dashboard first.
    </div>
  )
  if (loading) return <div className="flex items-center justify-center h-screen text-white text-xl">Generating insights...</div>
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4">
        <div className="text-red-400 text-xl">{error}</div>
        <button
          type="button"
          onClick={fetchInsights}
          className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
        >
          Retry loading insights
        </button>
      </div>
    )
  }

  return (
    <div id="insights-root" className="p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Strategy Insights</h1>
        <p className="text-gray-400 mt-1">Practical suggestions generated from your account data.</p>
        <p className="text-gray-500 mt-1 text-sm">
          These are strategy playbooks (when to run + action), not background posting bots.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <a
          href={`${apiBase}/reports/dashboard.pdf?username=${username}`}
          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-100 hover:bg-gray-700 border border-gray-700"
        >
          Download dashboard PDF (charts)
        </a>
      </div>
      <InsightsPanel data={insights} />

      <div className="bg-gray-900 rounded-2xl p-4">
        <h2 className="text-lg font-semibold mb-4 text-white">Action Playbooks</h2>
        {workflows.length === 0 ? (
          <p className="text-sm text-gray-400">No workflow suggestions available right now.</p>
        ) : (
          <div className="space-y-3">
            {workflows.map((workflow, index) => (
              <div key={index} className="border border-gray-700 rounded-xl p-3 bg-gray-950/40">
                <p className="text-white font-medium">{workflow.name}</p>
                <p className="text-sm text-gray-400 mt-1">Timing: {workflow.trigger}</p>
                <p className="text-sm text-gray-300 mt-1">{workflow.action}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
