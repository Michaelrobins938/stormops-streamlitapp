import routesData from '@/data/routes'

export default function Page() {
  const routes = routesData

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-2">Routes & Jobs</h1>
        <p className="text-gray-400">Manage crew assignments and job progress</p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-dark-200 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Active Routes</p>
          <p className="text-2xl font-bold text-primary">{routes.length}</p>
        </div>
        <div className="bg-dark-200 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Unassigned</p>
          <p className="text-2xl font-bold text-white">
            {routes.filter(r => r.status === 'pending').length}
          </p>
        </div>
        <div className="bg-dark-200 rounded-lg p-4">
          <p className="text-gray-400 text-sm">In Progress</p>
          <p className="text-2xl font-bold text-white">
            {routes.filter(r => r.status === 'in_progress').length}
          </p>
        </div>
        <div className="bg-dark-200 rounded-lg p-4">
          <p className="text-gray-400 text-sm">Completed</p>
          <p className="text-2xl font-bold text-green-500">
            {routes.filter(r => r.status === 'completed').length}
          </p>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-4 gap-4">
        {/* Unassigned */}
        <div className="bg-dark-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-gray-400"></span>
            Unassigned
          </h3>
          {routes.filter(r => r.status === 'pending').map(route => (
            <RouteCard key={route.id} route={route} />
          ))}
        </div>

        {/* Assigned */}
        <div className="bg-dark-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
            Assigned
          </h3>
          {routes.filter(r => r.status === 'assigned').map(route => (
            <RouteCard key={route.id} route={route} />
          ))}
        </div>

        {/* In Progress */}
        <div className="bg-dark-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
            In Progress
          </h3>
          {routes.filter(r => r.status === 'in_progress').map(route => (
            <RouteCard key={route.id} route={route} progress />
          ))}
        </div>

        {/* Completed */}
        <div className="bg-dark-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Completed
          </h3>
          {routes.filter(r => r.status === 'completed').map(route => (
            <RouteCard key={route.id} route={route} />
          ))}
        </div>
      </div>
    </div>
  )
}

function RouteCard({ route, progress = false }) {
  const completion = progress
    ? Math.round((route.completed_jobs / route.total_jobs) * 100)
    : 0

  return (
    <div className="bg-dark-100 rounded-lg p-3 mb-3 border border-gray-700 hover:border-primary transition-colors">
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-medium text-white">{route.name}</h4>
        <span className="text-xs text-gray-400">{route.zip_code}</span>
      </div>
      <p className="text-sm text-gray-400 mb-3">{route.property_count} properties</p>
      {route.assigned_crew && (
        <p className="text-sm text-primary mb-2">Crew: {route.assigned_crew}</p>
      )}
      {progress && (
        <div className="mt-2">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>{route.completed_jobs}/{route.total_jobs} done</span>
            <span>{completion}%</span>
          </div>
          <div className="w-full bg-dark-300 rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all"
              style={{ width: `${completion}%` }}
            ></div>
          </div>
        </div>
      )}
      <button className="mt-3 w-full py-2 bg-primary hover:bg-primary-light text-white rounded text-sm font-medium transition-colors">
        {progress ? 'View Jobs' : 'Assign Crew'}
      </button>
    </div>
  )
}
