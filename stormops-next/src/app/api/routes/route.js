import { NextResponse } from 'next/server'

let routes = [
  {
    id: 'route-001',
    name: 'North Dallas Premium',
    zip_code: '75201',
    property_count: 145,
    status: 'in_progress',
    assigned_crew: 'Crew A',
    total_jobs: 67,
    completed_jobs: 45,
    estimated_value: 18900000
  },
  {
    id: 'route-002',
    name: 'Plano East Cluster',
    zip_code: '75024',
    property_count: 98,
    status: 'assigned',
    assigned_crew: 'Crew B',
    total_jobs: 45,
    completed_jobs: 0,
    estimated_value: 12400000
  },
  {
    id: 'route-003',
    name: 'Frisco Central',
    zip_code: '75034',
    property_count: 124,
    status: 'pending',
    assigned_crew: null,
    total_jobs: 0,
    completed_jobs: 0,
    estimated_value: 16750000
  }
]

export async function GET() {
  return NextResponse.json(routes)
}

export async function PUT(request) {
  const body = await request.json()
  const { id, ...updates } = body

  routes = routes.map(route =>
    route.id === id ? { ...route, ...updates } : route
  )

  return NextResponse.json({ success: true, route: routes.find(r => r.id === id) })
}
