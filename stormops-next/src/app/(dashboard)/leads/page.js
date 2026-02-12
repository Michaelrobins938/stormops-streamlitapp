export default function Page() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Leads</h1>
      <div className="bg-dark-200 rounded-lg p-4">
        <table className="w-full">
          <thead>
            <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
              <th className="pb-3">Address</th>
              <th className="pb-3">ZIP</th>
              <th className="pb-3">Tier</th>
              <th className="pb-3">Score</th>
              <th className="pb-3">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-700">
              <td className="py-3 text-white">123 Oak St, Dallas</td>
              <td className="py-3 text-gray-400">75201</td>
              <td className="py-3"><span className="px-2 py-1 bg-red-500/20 text-red-500 rounded text-xs">Critical</span></td>
              <td className="py-3 text-primary">92</td>
              <td className="py-3 text-gray-400">Pending</td>
            </tr>
            <tr className="border-b border-gray-700">
              <td className="py-3 text-white">456 Maple Ave, Dallas</td>
              <td className="py-3 text-gray-400">75204</td>
              <td className="py-3"><span className="px-2 py-1 bg-red-500/20 text-red-500 rounded text-xs">Critical</span></td>
              <td className="py-3 text-primary">88</td>
              <td className="py-3 text-gray-400">Contacted</td>
            </tr>
            <tr className="border-b border-gray-700">
              <td className="py-3 text-white">789 Pine Rd, Plano</td>
              <td className="py-3 text-gray-400">75024</td>
              <td className="py-3"><span className="px-2 py-1 bg-orange-500/20 text-orange-500 rounded text-xs">High</span></td>
              <td className="py-3 text-primary">78</td>
              <td className="py-3 text-gray-400">Pending</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
