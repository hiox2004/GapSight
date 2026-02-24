import { useEffect, useState } from 'react'
import api from '../api/axios'
import InsightsPanel from '../components/InsightsPanel'

export default function Insights() {
  const [insights, setInsights] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const res = await api.get('/insights/')
        setInsights(res.data)
      } catch (err) {
        setError('Failed to load insights.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchInsights()
  }, [])

  if (loading) return <div className="flex items-center justify-center h-screen text-white text-xl">Generating insights...</div>
  if (error) return <div className="flex items-center justify-center h-screen text-red-400 text-xl">{error}</div>

  return (
    <div className="p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Strategy Insights</h1>
        <p className="text-gray-400 mt-1">Practical suggestions generated from your account data.</p>
      </div>
      <InsightsPanel data={insights} />
    </div>
  )
}
