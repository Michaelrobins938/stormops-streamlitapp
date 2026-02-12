export default function Page() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Property Data</h1>
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-dark-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-2">Import Properties</h3>
          <p className="text-gray-400 text-sm mb-4">Upload CSV with property addresses</p>
          <button className="w-full py-2 bg-primary text-white rounded font-medium">Upload CSV</button>
        </div>
        <div className="bg-dark-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-2">Vulnerability Score</h3>
          <p className="text-3xl font-bold text-primary">0.82</p>
          <p className="text-gray-400 text-sm">Portfolio average</p>
        </div>
        <div className="bg-dark-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-2">Properties Loaded</h3>
          <p className="text-3xl font-bold text-white">0</p>
          <p className="text-gray-400 text-sm">Import to begin</p>
        </div>
      </div>
    </div>
  )
}
