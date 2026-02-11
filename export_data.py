"""
Export StormOps data to CSV/JSON
"""

import psycopg2
import csv
import json
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD


def export_leads_csv(event_id, output_file='leads.csv'):
    """Export leads to CSV"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.parcel_id, p.address, p.zip_code, is.sii_score, is.hail_intensity_mm,
                   l.lead_status, l.created_at
            FROM leads l
            JOIN parcels p ON l.parcel_id = p.id
            JOIN impact_scores is ON l.parcel_id = is.parcel_id AND l.event_id = is.event_id
            WHERE l.event_id = %s
            ORDER BY is.sii_score DESC
        """, (event_id,))
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Parcel ID', 'Address', 'ZIP', 'SII Score', 'Hail (mm)', 'Status', 'Created'])
            for row in cursor.fetchall():
                writer.writerow(row)
        
        cursor.close()
        conn.close()
        
        print(f"✅ Exported leads to {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")


def export_routes_json(event_id, output_file='routes.json'):
    """Export routes to JSON"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, route_name, canvasser_id, parcel_count, status
            FROM routes
            WHERE event_id = %s
            ORDER BY created_at DESC
        """, (event_id,))
        
        routes = []
        for row in cursor.fetchall():
            routes.append({
                'id': str(row[0]),
                'name': row[1],
                'canvasser': row[2],
                'parcel_count': row[3],
                'status': row[4],
            })
        
        with open(output_file, 'w') as f:
            json.dump(routes, f, indent=2)
        
        cursor.close()
        conn.close()
        
        print(f"✅ Exported routes to {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")


def export_metrics_json(event_id, output_file='metrics.json'):
    """Export metrics to JSON"""
    try:
        from sla_monitor import SLAMonitor
        from moe import MarkovOpportunityEngine
        
        monitor = SLAMonitor(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        monitor.connect()
        
        moe = MarkovOpportunityEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        moe.connect()
        
        metrics = monitor.get_dashboard_metrics(event_id)
        acceptance = monitor.get_claim_acceptance_rate(event_id)
        op_score = moe.get_operational_score(event_id)
        
        data = {
            'event_id': event_id,
            'timestamp': datetime.now().isoformat(),
            'dashboard_metrics': metrics,
            'claim_acceptance': acceptance,
            'operational_score': op_score,
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        monitor.close()
        moe.close()
        
        print(f"✅ Exported metrics to {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python export_data.py <event_id> [leads|routes|metrics|all]")
        sys.exit(1)
    
    event_id = sys.argv[1]
    export_type = sys.argv[2] if len(sys.argv) > 2 else 'all'
    
    if export_type in ['leads', 'all']:
        export_leads_csv(event_id)
    
    if export_type in ['routes', 'all']:
        export_routes_json(event_id)
    
    if export_type in ['metrics', 'all']:
        export_metrics_json(event_id)
