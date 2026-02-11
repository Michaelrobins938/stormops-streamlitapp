"""
StormOps Integration Script
Orchestrates all Stage 1-3 components end-to-end.
"""

import psycopg2
from datetime import datetime
import logging

from sii_scorer import SIIScorer
from earth2_ingestion import Earth2Ingestion
from proposal_engine import ProposalEngine
from route_optimizer import RouteOptimizer
from crm_integration import MockCRMIntegration
from moe import MarkovOpportunityEngine
from impact_report_generator import ImpactReportGenerator
from sla_monitor import SLAMonitor
from forecast_monitor import ForecastMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


def run_full_pipeline(event_id: str, zip_code: str = '75034'):
    """
    Run complete StormOps pipeline: Stage 1 → Stage 2 → Stage 3
    """
    
    logger.info("=" * 80)
    logger.info("STORMOPS FULL PIPELINE")
    logger.info("=" * 80)
    
    # Stage 1: Data & Scoring
    logger.info("\n[STAGE 1] Data & Scoring Foundation")
    logger.info("-" * 80)
    
    try:
        ingestion = Earth2Ingestion(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        ingestion.connect()
        
        # Update SII scores
        sii_count = ingestion.update_impact_scores_with_sii(event_id)
        logger.info(f"✅ Updated {sii_count} SII scores")
        
        ingestion.close()
    except Exception as e:
        logger.error(f"❌ Stage 1 error: {e}")
        return
    
    # Stage 2: Lead Gen & Route Building
    logger.info("\n[STAGE 2] Lead Gen & Route Building")
    logger.info("-" * 80)
    
    try:
        # Generate lead gen proposal
        engine = ProposalEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        engine.connect()
        
        lead_gen_id = engine.generate_lead_gen_proposal(
            event_id=event_id,
            zip_code=zip_code,
            sii_min=60,
        )
        logger.info(f"✅ Generated lead gen proposal: {lead_gen_id}")
        
        # Approve it
        engine.approve_proposal(lead_gen_id)
        logger.info(f"✅ Approved lead gen proposal")
        
        # Generate SMS campaign proposal
        sms_id = engine.generate_sms_campaign_proposal(
            event_id=event_id,
            zip_code=zip_code,
        )
        logger.info(f"✅ Generated SMS campaign proposal: {sms_id}")
        engine.approve_proposal(sms_id)
        
        engine.close()
        
        # Build routes
        optimizer = RouteOptimizer(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        optimizer.connect()
        
        route_ids = optimizer.build_routes(
            event_id=event_id,
            zip_code=zip_code,
            sii_min=70,
            num_canvassers=4,
        )
        logger.info(f"✅ Built {len(route_ids)} optimized routes")
        
        optimizer.close()
    
    except Exception as e:
        logger.error(f"❌ Stage 2 error: {e}")
        return
    
    # Stage 3: Operational Intelligence
    logger.info("\n[STAGE 3] Operational Intelligence")
    logger.info("-" * 80)
    
    try:
        # Initialize MOE
        moe = MarkovOpportunityEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        moe.connect()
        
        moe.initialize_sector_states(event_id)
        logger.info(f"✅ Initialized MOE sector states")
        
        # Get operational score
        op_score = moe.get_operational_score(event_id)
        logger.info(f"✅ Operational Score: {op_score:.1f}/100")
        
        moe.close()
        
        # Generate impact reports
        gen = ImpactReportGenerator(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        gen.connect()
        
        report_count = gen.generate_batch_reports(event_id, sii_min=75)
        logger.info(f"✅ Generated {report_count} impact reports")
        
        gen.close()
        
        # Check SLA metrics
        monitor = SLAMonitor(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        monitor.connect()
        
        metrics = monitor.get_dashboard_metrics(event_id)
        logger.info(f"✅ Dashboard Metrics:")
        logger.info(f"   - Total leads: {metrics.get('total_leads', 0)}")
        logger.info(f"   - Contact rate: {metrics.get('contact_rate', 0)}%")
        logger.info(f"   - Total claim value: ${metrics.get('total_claim_value', 0):,.0f}")
        
        monitor.close()
        
        # Check forecast
        fm = ForecastMonitor(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        
        forecast_data = [
            {'day': 1, 'severe_probability': 0.02, 'hail_probability': 0.01, 'max_wind_mph': 15},
            {'day': 2, 'severe_probability': 0.05, 'hail_probability': 0.03, 'max_wind_mph': 20},
            {'day': 3, 'severe_probability': 0.25, 'hail_probability': 0.30, 'max_wind_mph': 55},
        ]
        
        all_alerts = []
        for day_forecast in forecast_data:
            alerts = fm.check_forecast_alerts(event_id, day_forecast)
            all_alerts.extend(alerts)
        
        logger.info(f"✅ Forecast alerts: {len(all_alerts)}")
        for alert in all_alerts:
            logger.info(f"   - {alert['message']}")
    
    except Exception as e:
        logger.error(f"❌ Stage 3 error: {e}")
        return
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Event: {event_id}")
    logger.info(f"ZIP: {zip_code}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("\nNext steps:")
    logger.info("1. Review proposals in StormOps UI")
    logger.info("2. Approve lead gen and SMS campaigns")
    logger.info("3. Push routes to field reps")
    logger.info("4. Monitor SLA and claim acceptance metrics")
    logger.info("5. Track forecast alerts for secondary storms")


if __name__ == '__main__':
    # Get event ID from database
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM events WHERE status = 'active' LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            event_id = result[0]
            run_full_pipeline(event_id)
        else:
            logger.error("No active events found. Run load_test_data.py first.")
    except Exception as e:
        logger.error(f"Error: {e}")
