"""
Real-time monitoring dashboard (terminal-based)
"""

import psycopg2
import time
import os
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD
from sla_monitor import SLAMonitor
from moe import MarkovOpportunityEngine


def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


def get_event_stats(event_id):
    """Get event statistics"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Event info
        cursor.execute("""
            SELECT name, peak_hail_inches, max_wind_mph, estimated_value_usd
            FROM events WHERE id = %s
        """, (event_id,))
        event = cursor.fetchone()
        
        # Lead stats
        cursor.execute("""
            SELECT COUNT(*), 
                   COUNT(CASE WHEN lead_status != 'new' THEN 1 END),
                   COUNT(CASE WHEN lead_status = 'closed' THEN 1 END)
            FROM leads WHERE event_id = %s
        """, (event_id,))
        leads = cursor.fetchone()
        
        # Route stats
        cursor.execute("""
            SELECT COUNT(*), COUNT(CASE WHEN status = 'completed' THEN 1 END)
            FROM routes WHERE event_id = %s
        """, (event_id,))
        routes = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            'event': event,
            'leads': leads,
            'routes': routes,
        }
    except Exception as e:
        return None


def display_dashboard(event_id):
    """Display real-time dashboard"""
    
    monitor = SLAMonitor(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
    monitor.connect()
    
    moe = MarkovOpportunityEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
    moe.connect()
    
    try:
        while True:
            clear_screen()
            
            print("=" * 80)
            print("STORMOPS REAL-TIME MONITOR")
            print("=" * 80)
            print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            stats = get_event_stats(event_id)
            
            if not stats:
                print("No event data available")
                break
            
            event = stats['event']
            leads = stats['leads']
            routes = stats['routes']
            
            # Event info
            print(f"Event: {event[0]}")
            print(f"  Peak Hail: {event[1]}\"")
            print(f"  Max Wind: {event[2]} mph")
            print(f"  Est. Value: ${event[3]:,.0f}\n")
            
            # Lead stats
            total_leads = leads[0] or 0
            contacted = leads[1] or 0
            closed = leads[2] or 0
            contact_rate = (contacted / total_leads * 100) if total_leads > 0 else 0
            close_rate = (closed / total_leads * 100) if total_leads > 0 else 0
            
            print(f"Leads:")
            print(f"  Total: {total_leads}")
            print(f"  Contacted: {contacted} ({contact_rate:.1f}%)")
            print(f"  Closed: {closed} ({close_rate:.1f}%)\n")
            
            # Route stats
            total_routes = routes[0] or 0
            completed_routes = routes[1] or 0
            
            print(f"Routes:")
            print(f"  Total: {total_routes}")
            print(f"  Completed: {completed_routes}\n")
            
            # SLA metrics
            metrics = monitor.get_dashboard_metrics(event_id)
            print(f"Claim Value: ${metrics.get('total_claim_value', 0):,.0f}\n")
            
            # Operational score
            op_score = moe.get_operational_score(event_id)
            print(f"Operational Score: {op_score:.1f}/100\n")
            
            # SLA breaches
            breaches = monitor.check_sla_breaches(event_id)
            print(f"SLA Breaches: {len(breaches)}")
            if breaches:
                for breach in breaches[:3]:
                    print(f"  ⚠️  {breach['address']}: {breach['minutes_elapsed']} min")
            
            print("\n" + "=" * 80)
            print("Press Ctrl+C to exit. Refreshing in 30 seconds...")
            
            time.sleep(30)
    
    except KeyboardInterrupt:
        print("\nMonitor stopped")
    finally:
        monitor.close()
        moe.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python monitor.py <event_id>")
        sys.exit(1)
    
    event_id = sys.argv[1]
    display_dashboard(event_id)
