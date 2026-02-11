#!/usr/bin/env python3
"""
StormOps CLI
Manual operations and debugging
"""

import click
import psycopg2
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

from proposal_engine import ProposalEngine
from route_optimizer import RouteOptimizer
from moe import MarkovOpportunityEngine
from impact_report_generator import ImpactReportGenerator
from sla_monitor import SLAMonitor
from forecast_monitor import ForecastMonitor


@click.group()
def cli():
    """StormOps CLI"""
    pass


@cli.command()
def list_events():
    """List active events"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, peak_hail_inches, max_wind_mph, estimated_value_usd, status
            FROM events
            ORDER BY event_date DESC
            LIMIT 10
        """)
        
        click.echo("\nActive Events:")
        for row in cursor.fetchall():
            click.echo(f"  {row[1]}: {row[2]}\" hail, {row[3]} mph wind, ${row[4]:,.0f} ({row[5]})")
        
        cursor.close()
        conn.close()
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.option('--event-id', prompt='Event ID', help='Event ID')
@click.option('--zip-code', default='75034', help='ZIP code')
def gen_leads(event_id, zip_code):
    """Generate leads"""
    try:
        engine = ProposalEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        engine.connect()
        
        proposal_id = engine.generate_lead_gen_proposal(
            event_id=event_id,
            zip_code=zip_code,
            sii_min=60,
        )
        
        click.echo(f"✅ Generated proposal: {proposal_id}")
        engine.close()
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@cli.command()
@click.option('--event-id', prompt='Event ID', help='Event ID')
@click.option('--zip-code', default='75034', help='ZIP code')
def build_routes(event_id, zip_code):
    """Build routes"""
    try:
        optimizer = RouteOptimizer(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        optimizer.connect()
        
        route_ids = optimizer.build_routes(
            event_id=event_id,
            zip_code=zip_code,
            sii_min=70,
            num_canvassers=4,
        )
        
        click.echo(f"✅ Built {len(route_ids)} routes")
        for rid in route_ids:
            click.echo(f"  - {rid}")
        
        optimizer.close()
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@cli.command()
@click.option('--event-id', prompt='Event ID', help='Event ID')
def gen_reports(event_id):
    """Generate impact reports"""
    try:
        gen = ImpactReportGenerator(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        gen.connect()
        
        count = gen.generate_batch_reports(event_id, sii_min=75)
        
        click.echo(f"✅ Generated {count} impact reports")
        gen.close()
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@cli.command()
@click.option('--event-id', prompt='Event ID', help='Event ID')
def check_sla(event_id):
    """Check SLA metrics"""
    try:
        monitor = SLAMonitor(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        monitor.connect()
        
        metrics = monitor.get_dashboard_metrics(event_id)
        
        click.echo("\nDashboard Metrics:")
        click.echo(f"  Total leads: {metrics.get('total_leads', 0)}")
        click.echo(f"  Contacted: {metrics.get('contacted_leads', 0)} ({metrics.get('contact_rate', 0)}%)")
        click.echo(f"  Inspected: {metrics.get('inspected_leads', 0)}")
        click.echo(f"  Closed: {metrics.get('closed_leads', 0)} ({metrics.get('close_rate', 0)}%)")
        click.echo(f"  Total claim value: ${metrics.get('total_claim_value', 0):,.0f}")
        
        breaches = monitor.check_sla_breaches(event_id)
        click.echo(f"\nSLA Breaches: {len(breaches)}")
        for breach in breaches[:5]:
            click.echo(f"  - {breach['address']}: {breach['minutes_elapsed']} min")
        
        monitor.close()
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@cli.command()
@click.option('--event-id', prompt='Event ID', help='Event ID')
def get_op_score(event_id):
    """Get operational score"""
    try:
        moe = MarkovOpportunityEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        moe.connect()
        
        score = moe.get_operational_score(event_id)
        
        click.echo(f"\nOperational Score: {score:.1f}/100")
        
        if score < 20:
            phase = "Baseline"
        elif score < 40:
            phase = "Risk"
        elif score < 60:
            phase = "Impact"
        elif score < 80:
            phase = "Recovery"
        else:
            phase = "Catastrophic"
        
        click.echo(f"Phase: {phase}")
        
        moe.close()
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@cli.command()
def test_components():
    """Test all components"""
    click.echo("\nTesting components...")
    
    from sii_scorer import SIIScorer
    scorer = SIIScorer()
    result = scorer.score(50, 'asphalt', 10)
    click.echo(f"✅ SII Scorer: {result['sii_score']}")
    
    from moe import MarkovOpportunityEngine
    moe = MarkovOpportunityEngine()
    click.echo(f"✅ MOE: OK")
    
    from impact_report_generator import ImpactReportGenerator
    gen = ImpactReportGenerator()
    click.echo(f"✅ Impact Report Generator: OK")
    
    from sla_monitor import SLAMonitor
    monitor = SLAMonitor()
    click.echo(f"✅ SLA Monitor: OK")
    
    from forecast_monitor import ForecastMonitor
    fm = ForecastMonitor()
    click.echo(f"✅ Forecast Monitor: OK")
    
    from crm_integration import MockCRMIntegration
    crm = MockCRMIntegration()
    click.echo(f"✅ CRM Integration: OK")
    
    click.echo("\n✅ All components OK")


if __name__ == '__main__':
    cli()
