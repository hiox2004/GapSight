export default function MetricCard({ title, value, subtitle, icon}){
    return (
        <div className="bf-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-2">
            <div className="flex gap-2 items-center justify-between text-gray-400 text-sm">
                <span>{title}</span>
                <span>{icon}</span>
            </div>
            <p className="text-3xl font-bold text-white">{value}</p>
            <p className="text-xs text-gray-500">{subtitle}</p>
        </div>
    )
}