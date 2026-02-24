import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, Lightbulb, Menu, X } from 'lucide-react'

const links = [
  { to: '/', icon: <LayoutDashboard size={18} />, label: 'Dashboard' },
  { to: '/competitors', icon: <Users size={18} />, label: 'Competitors' },
  { to: '/insights', icon: <Lightbulb size={18} />, label: 'Insights' },
]

export default function Sidebar() {
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4 py-3">
        <h1 className="text-lg font-bold text-white">  GapSight</h1>
        <button onClick={() => setOpen(!open)} className="text-gray-400 hover:text-white">
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile dropdown menu */}
      {open && (
        <div className="md:hidden fixed top-12 left-0 right-0 z-40 bg-gray-900 border-b border-gray-800 flex flex-col p-4 gap-2">
          {links.map(({ to, icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              {icon}{label}
            </NavLink>
          ))}
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-56 bg-gray-900 border-r border-gray-800 flex-col p-4 gap-2">
        <h1 className="text-xl font-bold text-white mb-6 pl-5">   GapSight</h1>
        {links.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            {icon}{label}
          </NavLink>
        ))}
      </aside>
    </>
  )
}
