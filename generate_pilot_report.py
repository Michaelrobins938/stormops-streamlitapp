"""
Pilot Report Generator - Create one-page reports for each pilot
Usage: python generate_pilot_report.py <tenant_id> <storm_id>
"""

import sys
from sqlalchemy import create_engine, text
import uuid
from datetime import datetime

def generate_report(tenant_id: uuid.UUID, storm_id: uuid.UUID = None):
    """Generate pilot report with lift numbers and ROI."""
    
    engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')
    
    with engine.connect() as conn:
        # Tenant info
        tenant = conn.execute(text("""
            SELECT org_name, contact_name, contact_email, pilot_start_date
            FROM tenants WHERE tenant_id = :tid
        """), {'tid': tenant_id}).fetchone()
        
        if not tenant:
            print(f"❌ Tenant {tenant_id} not found")
            return
        
        org_name = tenant[0]
        days_in_pilot = (datetime.now() - tenant[3]).days if tenant[3] else 0
        
        # Storm-specific or overall metrics
        if storm_id:
            storm_filter = f"AND storm_id = '{storm_id}'"
            storm_name = conn.execute(text("""
                SELECT name FROM storms WHERE storm_id = :sid
            """), {'sid': storm_id}).fetchone()[0]
        else:
            storm_filter = ""
            storm_name = "All Storms"
        
        # Routes
        routes = conn.execute(text(f"""
            SELECT COUNT(*) FROM routes 
            WHERE tenant_id = :tid {storm_filter}
        """), {'tid': tenant_id}).fetchone()[0]
        
        # Jobs
        jobs = conn.execute(text(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM jobs
            WHERE tenant_id = :tid {storm_filter}
        """), {'tid': tenant_id}).fetchone()
        
        total_jobs = jobs[0]
        completed_jobs = jobs[1] or 0
        completion_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        # Outcomes
        outcomes = conn.execute(text(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN actual_converted THEN 1 ELSE 0 END) as converted,
                SUM(conversion_value) as total_value,
                AVG(conversion_value) as avg_value
            FROM policy_outcomes
            WHERE tenant_id = :tid {storm_filter}
        """), {'tid': tenant_id}).fetchone()
        
        total_outcomes = outcomes[0]
        converted = outcomes[1] or 0
        total_value = outcomes[2] or 0
        avg_value = outcomes[3] or 0
        conversion_rate = (converted / total_outcomes * 100) if total_outcomes > 0 else 0
        
        # Treatment vs control (if we have both)
        treat_outcomes = conn.execute(text(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN actual_converted THEN 1 ELSE 0 END) as converted
            FROM policy_outcomes
            WHERE tenant_id = :tid {storm_filter} AND decision = 'treat'
        """), {'tid': tenant_id}).fetchone()
        
        hold_outcomes = conn.execute(text(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN actual_converted THEN 1 ELSE 0 END) as converted
            FROM policy_outcomes
            WHERE tenant_id = :tid {storm_filter} AND decision = 'hold'
        """), {'tid': tenant_id}).fetchone()
        
        treat_rate = (treat_outcomes[1] / treat_outcomes[0] * 100) if treat_outcomes[0] > 0 else 0
        hold_rate = (hold_outcomes[1] / hold_outcomes[0] * 100) if hold_outcomes[0] > 0 else 0
        lift = treat_rate - hold_rate
    
    # Generate report
    report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          STORMOPS PILOT REPORT                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

PILOT: {org_name}
CONTACT: {tenant[1]} ({tenant[2]})
STORM: {storm_name}
DURATION: {days_in_pilot} days
GENERATED: {datetime.now().strftime('%Y-%m-%d')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPERATIONAL METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Routes Generated:        {routes}
Total Jobs:              {total_jobs}
Jobs Completed:          {completed_jobs}
Completion Rate:         {completion_rate:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSION & ROI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Properties Contacted:    {total_outcomes}
Conversions:             {converted}
Conversion Rate:         {conversion_rate:.1f}%

Total Claim Value:       ${total_value:,.0f}
Avg Claim Value:         ${avg_value:,.0f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCREMENTALITY (TREAT VS HOLD)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Treated Properties:      {treat_outcomes[0]} ({treat_outcomes[1]} converted = {treat_rate:.1f}%)
Held Properties:         {hold_outcomes[0]} ({hold_outcomes[1]} converted = {hold_rate:.1f}%)

LIFT:                    {lift:+.1f} percentage points
INTERPRETATION:          {"StormOps targeting increased conversions" if lift > 0 else "No measurable lift yet"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUCCESS CRITERIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Routes per Storm:      {routes} (target: 3+)
{"✓" if completed_jobs >= 50 else "✗"} Jobs Completed:        {completed_jobs} (target: 50+)
{"✓" if completion_rate >= 80 else "✗"} Completion Rate:       {completion_rate:.1f}% (target: 80%+)
{"✓" if conversion_rate >= 20 else "✗"} Conversion Rate:       {conversion_rate:.1f}% (target: 20%+)

OVERALL STATUS:          {"🟢 PILOT SUCCESS" if (routes >= 3 and completed_jobs >= 50 and completion_rate >= 80) else "🟡 IN PROGRESS"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{"• Convert to paid tier" if (routes >= 3 and completed_jobs >= 50) else "• Continue pilot - track weekly progress"}
• Schedule feedback call
• Document learnings
• Use as case study for next pilots

╚══════════════════════════════════════════════════════════════════════════════╝
"""
    
    print(report)
    
    # Save to file
    filename = f"pilot_report_{org_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {filename}")
    
    return report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_pilot_report.py <tenant_id> [storm_id]")
        sys.exit(1)
    
    tenant_id = uuid.UUID(sys.argv[1])
    storm_id = uuid.UUID(sys.argv[2]) if len(sys.argv) > 2 else None
    
    generate_report(tenant_id, storm_id)
