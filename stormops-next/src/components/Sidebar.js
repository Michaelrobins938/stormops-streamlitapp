import Link from 'next/link'

const navItems = [
  { href: '/', label: 'Dashboard', icon: '📊' },
  { href: '/map', label: 'Storm Map', icon: '🗺️' },
  { href: '/leads', label: 'Leads', icon: '🎯' },
  { href: '/routes', label: 'Routes & Jobs', icon: '🚗' },
  { href: '/timeline', label: 'Timeline', icon: '📅' },
  { href: '/property', label: 'Property Data', icon: '🏠' },
]

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-dark-200 border-r border-gray-700 z-50">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-xl font-bold text-primary">StormOps</h1>
        <p className="text-xs text-gray-400">Earth-2 Intelligence</p>
      </div>
      <nav className="p-2">
        {navItems.map(item => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 px-4 py-3 text-gray-300 hover:bg-dark-100 hover:text-primary transition-colors rounded-lg mb-1"
          >
            <span className="text-lg">{item.icon}</span>
            <span className="font-medium">{item.label}</span>
          </Link>
        ))}
      </nav>
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-700">
        <p className="text-xs text-gray-500">Demo Storm: DFW-24</p>
        <p className="text-xs text-gray-500">Tenant: demo-tenant</p>
      </div>
    </aside>
  )
}
