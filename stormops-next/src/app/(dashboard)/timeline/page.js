export default function Page() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Timeline</h1>
      <div className="bg-dark-200 rounded-lg p-4">
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="w-32 text-gray-400">Now</div>
            <div className="flex-1 p-4 bg-dark-300 rounded-lg border-l-4 border-primary">
              <h3 className="text-white font-medium">Storm Impact</h3>
              <p className="text-gray-400 text-sm">Maximum intensity in DFW area</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="w-32 text-gray-400">+24h</div>
            <div className="flex-1 p-4 bg-dark-300 rounded-lg border-l-4 border-yellow-500">
              <h3 className="text-white font-medium">Initial Claims</h3>
              <p className="text-gray-400 text-sm">First wave of insurance claims expected</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="w-32 text-gray-400">+72h</div>
            <div className="flex-1 p-4 bg-dark-300 rounded-lg border-l-4 border-green-500">
              <h3 className="text-white font-medium">Route Planning</h3>
              <p className="text-gray-400 text-sm">Optimize crew routes for max coverage</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
