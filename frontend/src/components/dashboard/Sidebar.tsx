import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { href: '/dashboard', label: 'Overview' },
  { href: '/dashboard/usage', label: 'Usage' },
  { href: '/dashboard/models', label: 'Models' },
  { href: '/dashboard/settings', label: 'Settings' },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="fixed left-0 top-0 z-30 flex h-screen w-56 flex-col border-r border-white/[0.06] bg-[#0b0f14]">
      <div className="flex h-14 items-center border-b border-white/[0.06] px-6">
        <span className="text-lg font-semibold text-white">Dashboard</span>
      </div>
      <nav className="flex-1 space-y-0.5 p-3">
        {navItems.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.href}
              to={item.href}
              className={`block rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-white/[0.08] text-white'
                  : 'text-white/60 hover:bg-white/[0.04] hover:text-white/80'
              }`}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
