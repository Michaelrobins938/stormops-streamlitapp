export const routes = [
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

export const jobs = [
  {
    id: 'job-001',
    route_id: 'route-001',
    address: '123 Main St',
    status: 'completed',
    claim_amount: 18500,
    damage_type: 'hail',
    notes: 'Completed exterior inspection'
  },
  {
    id: 'job-002',
    route_id: 'route-001',
    address: '456 Oak Ave',
    status: 'in_progress',
    claim_amount: 0,
    damage_type: 'hail',
    notes: 'In-progress roof assessment'
  },
  {
    id: 'job-003',
    route_id: 'route-002',
    address: '789 Pine Rd',
    status: 'pending',
    claim_amount: 0,
    damage_type: 'hail',
    notes: 'Scheduled for tomorrow'
  },
  {
    id: 'job-004',
    route_id: 'route-002',
    address: '321 Elm Blvd',
    status: 'pending',
    claim_amount: 0,
    damage_type: 'wind',
    notes: 'Waiting for permit'
  }
]

export default { routes, jobs }
