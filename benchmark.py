"""
Performance benchmarking for StormOps
"""

import time
import psycopg2
from datetime import datetime
import logging

from sii_scorer import SIIScorer
from proposal_engine import ProposalEngine
from route_optimizer import RouteOptimizer
from impact_report_generator import ImpactReportGenerator
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Benchmark:
    """Benchmark StormOps components"""
    
    @staticmethod
    def benchmark_sii_scoring(iterations=1000):
        """Benchmark SII scoring"""
        logger.info(f"\n[BENCHMARK] SII Scoring ({iterations} iterations)")
        
        scorer = SIIScorer()
        
        start = time.time()
        for i in range(iterations):
            scorer.score(50, 'asphalt', 10)
        elapsed = time.time() - start
        
        per_call = (elapsed / iterations) * 1000
        logger.info(f"  Total: {elapsed:.2f}s")
        logger.info(f"  Per call: {per_call:.2f}ms")
        logger.info(f"  Throughput: {iterations / elapsed:.0f} calls/sec")
    
    @staticmethod
    def benchmark_proposal_generation(event_id):
        """Benchmark proposal generation"""
        logger.info(f"\n[BENCHMARK] Proposal Generation")
        
        engine = ProposalEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        engine.connect()
        
        start = time.time()
        proposal_id = engine.generate_lead_gen_proposal(event_id, '75034')
        elapsed = time.time() - start
        
        logger.info(f"  Lead gen proposal: {elapsed:.2f}s")
        
        start = time.time()
        proposal_id = engine.generate_route_build_proposal(event_id, '75034')
        elapsed = time.time() - start
        
        logger.info(f"  Route build proposal: {elapsed:.2f}s")
        
        start = time.time()
        proposal_id = engine.generate_sms_campaign_proposal(event_id, '75034')
        elapsed = time.time() - start
        
        logger.info(f"  SMS campaign proposal: {elapsed:.2f}s")
        
        engine.close()
    
    @staticmethod
    def benchmark_route_building(event_id):
        """Benchmark route building"""
        logger.info(f"\n[BENCHMARK] Route Building")
        
        optimizer = RouteOptimizer(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        optimizer.connect()
        
        start = time.time()
        route_ids = optimizer.build_routes(event_id, '75034', sii_min=70, num_canvassers=4)
        elapsed = time.time() - start
        
        logger.info(f"  Built {len(route_ids)} routes in {elapsed:.2f}s")
        logger.info(f"  Per route: {elapsed / len(route_ids):.2f}s")
        
        optimizer.close()
    
    @staticmethod
    def benchmark_impact_reports(event_id):
        """Benchmark impact report generation"""
        logger.info(f"\n[BENCHMARK] Impact Report Generation")
        
        gen = ImpactReportGenerator(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        gen.connect()
        
        start = time.time()
        count = gen.generate_batch_reports(event_id, sii_min=75)
        elapsed = time.time() - start
        
        logger.info(f"  Generated {count} reports in {elapsed:.2f}s")
        logger.info(f"  Per report: {elapsed / count * 1000:.2f}ms")
        
        gen.close()
    
    @staticmethod
    def benchmark_database_queries(event_id):
        """Benchmark database queries"""
        logger.info(f"\n[BENCHMARK] Database Queries")
        
        try:
            conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
            )
            cursor = conn.cursor()
            
            # Query 1: Get high-SII parcels
            start = time.time()
            cursor.execute("""
                SELECT COUNT(*) FROM impact_scores
                WHERE event_id = %s AND sii_score >= 60
            """, (event_id,))
            cursor.fetchone()
            elapsed = time.time() - start
            logger.info(f"  High-SII parcel count: {elapsed * 1000:.2f}ms")
            
            # Query 2: Get routes
            start = time.time()
            cursor.execute("""
                SELECT COUNT(*) FROM routes WHERE event_id = %s
            """, (event_id,))
            cursor.fetchone()
            elapsed = time.time() - start
            logger.info(f"  Route count: {elapsed * 1000:.2f}ms")
            
            # Query 3: Get leads
            start = time.time()
            cursor.execute("""
                SELECT COUNT(*) FROM leads WHERE event_id = %s
            """, (event_id,))
            cursor.fetchone()
            elapsed = time.time() - start
            logger.info(f"  Lead count: {elapsed * 1000:.2f}ms")
            
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error: {e}")


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("STORMOPS PERFORMANCE BENCHMARKS")
    logger.info("=" * 80)
    
    # Get event ID
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
            
            Benchmark.benchmark_sii_scoring(1000)
            Benchmark.benchmark_database_queries(event_id)
            Benchmark.benchmark_proposal_generation(event_id)
            Benchmark.benchmark_route_building(event_id)
            Benchmark.benchmark_impact_reports(event_id)
            
            logger.info("\n" + "=" * 80)
            logger.info("BENCHMARKS COMPLETE")
            logger.info("=" * 80)
        else:
            logger.error("No active events found")
    except Exception as e:
        logger.error(f"Error: {e}")
