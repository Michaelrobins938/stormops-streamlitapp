export default function Page() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Dashboard</h1>
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-dark-200 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Active Storm</p>
          <p className="text-2xl font-bold text-primary">DFW Storm-24</p>
        </div>
        <div className="bg-dark-200 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Impact Zones</p>
          <p className="text-2xl font-bold text-white">18</p>
        </div>
        <div className="bg-dark-200 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Total Leads</p>
          <p className="text-2xl font-bold text-white">10</p>
        </div>
        <div className="bg-dark-200 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Route Completion</p>
          <p className="text-2xl font-bold text-green-500">45%</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-dark-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Impact Map</h3>
          <div className="h-64 bg-dark-300 rounded-lg flex items-center justify-center text-gray-400">
            Map placeholder - Earth-2 visualization
          </div>
        </div>
        <div className="bg-dark-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4">High Priority Leads</h3>
          <div className="space-y-2">
            <div className="flex justify-between items-center p-2 bg-dark-300 rounded">
              <span className="text-white">123 Oak St, Dallas</span>
              <span className="text-primary text-sm">Critical</span>
            </div>
            <div className="flex justify-between items-center p-2 bg-dark-300 rounded">
              <span className="text-white">456 Maple Ave, Dallas</span>
              <span className="text-primary text-sm">Critical</span>
            </div>
            <div className="flex justify-between items-center p-2 bg-dark-300 rounded">
              <span className="text-white">789 Pine Rd, Plano</span>
              <span className="text-yellow-500 text-sm">High</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
