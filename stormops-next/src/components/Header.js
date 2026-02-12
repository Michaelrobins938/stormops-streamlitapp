'use client'

import { useState } from 'react'

export default function Header() {
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <header className="h-16 bg-dark-200 border-b border-gray-700 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <div className="relative">
          <input
            type="text"
            placeholder="Search addresses, ZIPs, routes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-80 bg-dark-300 border border-gray-600 rounded-lg px-4 py-2 pl-10 text-white placeholder-gray-400 focus:outline-none focus:border-primary"
          />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <button className="px-4 py-2 bg-primary hover:bg-primary-light text-white rounded-lg font-medium transition-colors">
          Generate Routes
        </button>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white font-bold">
            DR
          </div>
          <span className="text-sm text-gray-300">Demo User</span>
        </div>
      </div>
    </header>
  )
}
