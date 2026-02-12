export default function Page() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Storm Map</h1>
      <div className="bg-dark-200 rounded-lg p-4 h-[600px]">
        <div className="flex justify-between mb-4">
          <div className="flex gap-2">
            <button className="px-4 py-2 bg-primary text-white rounded font-medium">ZIP View</button>
            <button className="px-4 py-2 bg-dark-300 text-gray-400 rounded">Grid View</button>
            <button className="px-4 py-2 bg-dark-300 text-gray-400 rounded">2km Downscaled</button>
          </div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500"></span>
              <span className="text-sm text-gray-400">Critical</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-orange-500"></span>
              <span className="text-sm text-gray-400">High</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
              <span className="text-sm text-gray-400">Medium</span>
            </div>
          </div>
        </div>
        <div className="h-[500px] bg-dark-300 rounded-lg flex items-center justify-center text-gray-400">
          Earth-2 Storm Map Visualization
        </div>
      </div>
    </div>
  )
}
