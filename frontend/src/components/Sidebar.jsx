import { NavLink } from "react-router-dom"
import { LayoutDashboard, Users, Lightbulb } from "lucide-react"

const links = [
    { to: "/", icon: <LayoutDashboard size={18} />, label: "Dashboard" },
    { to: "/competitors", icon: <Users size={18} />, label: "Competitors" },
    { to: "/insights", icon: <Lightbulb size={18} />, label: "Insights" },
]

export default function Sidebar() {
  return (
    <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col p-4 gap-2">
        <h1 className="text-xl font-bold text-white mb-6"> GapSight </h1>
        {links.map(({ to, icon, label}) => (
            <NavLink key={to} to={to} end className={({isActive})=>
            `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
              isActive
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            }`}>
                {icon}
                {label}
            </NavLink>
        ))}
    </aside>
  )
}