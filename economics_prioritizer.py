"""
Economics and Prioritization Layer
Ranks Proposals by expected profit under constraints
"""

import psycopg2
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class EconomicsPrioritizer:
    """Rank Proposals by ROI and profit"""
    
    def __init__(self):
        self.conn = None
        self.cac_per_lead = 50  # Cost to acquire lead ($)
        self.margin_pct = 0.15  # Margin on job (15%)
        self.rep_hourly_cost = 50  # Rep cost per hour ($)
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def compute_parcel_economics(self, event_id: str):
        """Compute economics for all parcels"""
        logger.info(f"Computing economics for event {event_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get all parcel impacts
            cursor.execute("""
                SELECT pi.parcel_id, pi.sii_score, pi.damage_probability
                FROM parcel_impacts pi
                WHERE pi.event_id = %s
            """, (event_id,))
            
            parcels = cursor.fetchall()
            
            for parcel_id, sii_score, damage_prob in parcels:
                # Estimate claim value (mock: $5k per SII point)
                estimated_claim = sii_score * 5000
                
                # Estimate profit
                estimated_profit = (estimated_claim * self.margin_pct) - self.cac_per_lead
                
                # ROI ratio
                roi = estimated_profit / self.cac_per_lead if self.cac_per_lead > 0 else 0
                
                # Priority score (0-100)
                priority = min(100, (roi * 10) + (damage_prob * 50))
                
                cursor.execute("""
                    INSERT INTO parcel_economics (
                        event_id, parcel_id, sii_score, estimated_claim_value_usd,
                        estimated_margin_pct, estimated_profit_usd, cac_budget_usd,
                        roi_ratio, priority_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id, parcel_id) DO UPDATE
                    SET priority_score = EXCLUDED.priority_score
                """, (
                    event_id, parcel_id, sii_score, estimated_claim,
                    self.margin_pct, estimated_profit, self.cac_per_lead,
                    roi, priority
                ))
            
            self.conn.commit()
            logger.info(f"Computed economics for {len(parcels)} parcels")
            
        except Exception as e:
            logger.error(f"Error computing economics: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def rank_proposals(self, event_id: str) -> list:
        """Rank pending Proposals by expected profit"""
        logger.info(f"Ranking proposals for event {event_id}")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT p.id, p.proposal_type, p.expected_leads, p.expected_value_usd,
                       COUNT(pe.id) as high_priority_parcels
                FROM proposals p
                LEFT JOIN parcel_economics pe ON p.event_id = pe.event_id
                    AND pe.priority_score >= 70
                WHERE p.event_id = %s AND p.status = 'pending'
                GROUP BY p.id, p.proposal_type, p.expected_leads, p.expected_value_usd
                ORDER BY p.expected_value_usd DESC
            """, (event_id,))
            
            proposals = []
            for row in cursor.fetchall():
                proposals.append({
                    'id': row[0],
                    'type': row[1],
                    'expected_leads': row[2],
                    'expected_value': row[3],
                    'high_priority_parcels': row[4],
                })
            
            logger.info(f"Ranked {len(proposals)} proposals")
            return proposals
        
        except Exception as e:
            logger.error(f"Error ranking proposals: {e}")
            return []
        finally:
            cursor.close()
    
    def optimize_lead_selection(self, event_id: str, budget_usd: float, max_leads: int) -> list:
        """Select top leads by ROI within budget"""
        logger.info(f"Optimizing lead selection: budget ${budget_usd}, max {max_leads} leads")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT parcel_id, priority_score, estimated_profit_usd
                FROM parcel_economics
                WHERE event_id = %s
                ORDER BY priority_score DESC
                LIMIT %s
            """, (event_id, max_leads))
            
            leads = []
            total_cost = 0
            
            for parcel_id, priority, profit in cursor.fetchall():
                cost = self.cac_per_lead
                if total_cost + cost <= budget_usd:
                    leads.append({
                        'parcel_id': parcel_id,
                        'priority': priority,
                        'expected_profit': profit,
                    })
                    total_cost += cost
            
            logger.info(f"Selected {len(leads)} leads, total cost ${total_cost}")
            return leads
        
        except Exception as e:
            logger.error(f"Error optimizing lead selection: {e}")
            return []
        finally:
            cursor.close()


class OutcomeTracker:
    """Track lead outcomes and update models"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def record_outcome(self, event_id: str, parcel_id: str, lead_id: str, 
                      status: str, job_amount: float = 0, claim_amount: float = 0):
        """Record lead outcome"""
        logger.info(f"Recording outcome: {parcel_id} → {status}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get predicted SII
            cursor.execute("""
                SELECT sii_score FROM parcel_impacts
                WHERE event_id = %s AND parcel_id = %s
            """, (event_id, parcel_id))
            
            result = cursor.fetchone()
            sii_predicted = result[0] if result else 0
            
            # Insert outcome
            cursor.execute("""
                INSERT INTO lead_outcomes (
                    event_id, parcel_id, lead_id, sii_score_predicted,
                    lead_status, job_amount_usd, claim_amount_usd
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id, parcel_id) DO UPDATE
                SET lead_status = EXCLUDED.lead_status,
                    job_amount_usd = EXCLUDED.job_amount_usd,
                    claim_amount_usd = EXCLUDED.claim_amount_usd
            """, (
                event_id, parcel_id, lead_id, sii_predicted,
                status, job_amount, claim_amount
            ))
            
            self.conn.commit()
            logger.info(f"Recorded outcome")
            
        except Exception as e:
            logger.error(f"Error recording outcome: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def compute_model_accuracy(self, event_id: str) -> dict:
        """Compute SII model accuracy"""
        logger.info(f"Computing model accuracy for event {event_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Compare predicted vs actual
            cursor.execute("""
                SELECT 
                    AVG(ABS(sii_score_predicted - (CASE WHEN claim_amount_usd > 0 THEN 80 ELSE 20 END))) as mae,
                    COUNT(*) as total_outcomes,
                    COUNT(CASE WHEN claim_amount_usd > 0 THEN 1 END) as claims_filed
                FROM lead_outcomes
                WHERE event_id = %s
            """, (event_id,))
            
            result = cursor.fetchone()
            
            return {
                'mean_absolute_error': result[0] or 0,
                'total_outcomes': result[1] or 0,
                'claims_filed': result[2] or 0,
            }
        
        except Exception as e:
            logger.error(f"Error computing accuracy: {e}")
            return {}
        finally:
            cursor.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python economics_prioritizer.py <event_id>")
        sys.exit(1)
    
    event_id = sys.argv[1]
    
    # Compute economics
    prioritizer = EconomicsPrioritizer()
    prioritizer.connect()
    prioritizer.compute_parcel_economics(event_id)
    
    # Rank proposals
    proposals = prioritizer.rank_proposals(event_id)
    print(f"\nRanked Proposals:")
    for p in proposals:
        print(f"  {p['type']}: ${p['expected_value']:,.0f}")
    
    # Optimize lead selection
    leads = prioritizer.optimize_lead_selection(event_id, budget_usd=50000, max_leads=1000)
    print(f"\nOptimized {len(leads)} leads within budget")
    
    prioritizer.close()
