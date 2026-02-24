export default function InsightsPanel({ data }) {
  if (!data) return <p className="text-gray-400">No insights available.</p>
  const recommendations = Array.isArray(data.recommendations) ? data.recommendations : []

  return (
    <div className="space-y-6">

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-indigo-400 uppercase tracking-wide mb-2">
            What Competitors Do Better
          </h3>
          <p className="text-gray-300 text-sm leading-relaxed">
            {data.what_competitors_do_better}
          </p>
        </div>

        <div className="bg-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-pink-400 uppercase tracking-wide mb-2">
            Content Gaps
          </h3>
          <p className="text-gray-300 text-sm leading-relaxed">
            {data.content_gaps}
          </p>
        </div>

        <div className="bg-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-yellow-400 uppercase tracking-wide mb-2">
            Best Time to Post
          </h3>
          <p className="text-gray-300 text-sm leading-relaxed">
            {data.best_time_to_post}
          </p>
        </div>

        <div className="bg-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-emerald-400 uppercase tracking-wide mb-2">
            Recommendations
          </h3>
          {recommendations.length === 0 ? (
            <p className="text-gray-400 text-sm">No recommendations available yet.</p>
          ) : (
            <ul className="space-y-2">
              {recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-gray-300 text-sm">
                  <span className="text-emerald-400 font-bold mt-0.5">→</span>
                  {rec}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

    </div>
  )
}
