"""
End-to-End Storm Test: DFW Storm 24
Full cycle validation with KPI tracking
"""

import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
import json

class StormE2ETest:
    """End-to-end test for complete storm cycle."""
    
    def __init__(self, event_id='DFW_STORM_24'):
        self.event_id = event_id
        self.results = {}
        self.engine = create_engine('sqlite:///stormops_attribution.db')
    
    def run_full_cycle(self):
        """Execute complete storm response cycle."""
        
        print("=" * 60)
        print(f"END-TO-END TEST: {self.event_id}")
        print("=" * 60)
        
        # Phase 1: Physics → SII_v2
        print("\n[1/6] Physics → SII_v2 Scoring...")
        self.test_sii_scoring()
        
        # Phase 2: Enrichment → Personas
        print("\n[2/6] Enrichment → Personas...")
        self.test_persona_assignment()
        
        # Phase 3: Uplift → Next Best Action
        print("\n[3/6] Uplift → Next Best Action...")
        self.test_uplift_models()
        
        # Phase 4: Journey Generation
        print("\n[4/6] Journey Generation...")
        self.test_journey_generation()
        
        # Phase 5: Attribution
        print("\n[5/6] Attribution (Markov + Shapley)...")
        self.test_attribution()
        
        # Phase 6: Strategic Plays
        print("\n[6/6] Strategic Plays...")
        self.test_strategic_plays()
        
        # Calculate KPIs
        print("\n" + "=" * 60)
        print("KPI SUMMARY")
        print("=" * 60)
        self.calculate_kpis()
        
        # Save results
        self.save_results()
        
        return self.results
    
    def test_sii_scoring(self):
        """Test SII_v2 scoring."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as total, AVG(sii_v2_score) as avg_score
                FROM sii_v2_scores
            """)).fetchone()
            
            self.results['sii_v2'] = {
                'total_scored': result[0],
                'avg_score': result[1],
                'status': 'PASS' if result[0] > 0 else 'FAIL'
            }
            
            print(f"  ✓ Scored {result[0]} properties")
            print(f"  ✓ Avg SII_v2: {result[1]:.2f}")
    
    def test_persona_assignment(self):
        """Test persona assignment."""
        leads = pd.read_csv('/home/forsythe/kirocli/kirocli/a_tier_leads.csv')
        
        persona_dist = leads['primary_persona'].value_counts()
        
        self.results['personas'] = {
            'total_assigned': len(leads),
            'distribution': persona_dist.to_dict(),
            'status': 'PASS' if len(leads) > 0 else 'FAIL'
        }
        
        print(f"  ✓ Assigned {len(leads)} personas")
        print(f"  ✓ Top persona: {persona_dist.index[0]} ({persona_dist.iloc[0]})")
    
    def test_uplift_models(self):
        """Test uplift model predictions."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as total, AVG(expected_uplift) as avg_uplift
                FROM lead_uplift
            """)).fetchone()
            
            self.results['uplift'] = {
                'total_predictions': result[0] if result[0] else 0,
                'avg_uplift': result[1] if result[1] else 0,
                'status': 'PASS' if result[0] and result[0] > 0 else 'WARN'
            }
            
            print(f"  ✓ Generated {result[0] or 0} uplift predictions")
            print(f"  ✓ Avg uplift: {result[1] or 0:.3f}")
    
    def test_journey_generation(self):
        """Test journey generation."""
        engine_journeys = create_engine('sqlite:///stormops_journeys.db')
        
        with engine_journeys.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT property_id) as unique_properties,
                    SUM(CAST(converted AS INTEGER)) as conversions
                FROM customer_journeys
                WHERE event_id = :eid
            """), {'eid': self.event_id}).fetchone()
            
            self.results['journeys'] = {
                'total_events': result[0],
                'unique_properties': result[1],
                'conversions': result[2],
                'conversion_rate': result[2] / result[1] if result[1] > 0 else 0,
                'status': 'PASS' if result[0] > 0 else 'FAIL'
            }
            
            print(f"  ✓ Generated {result[0]} journey events")
            print(f"  ✓ {result[1]} unique properties")
            print(f"  ✓ {result[2]} conversions ({result[2]/result[1]*100:.1f}%)")
    
    def test_attribution(self):
        """Test attribution calculation."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as channels,
                    SUM(credit) as total_credit,
                    MAX(conversions) as conversions
                FROM channel_attribution
                WHERE event_id = :eid
            """), {'eid': self.event_id}).fetchone()
            
            self.results['attribution'] = {
                'channels_attributed': result[0],
                'total_credit': result[1],
                'conversions': result[2],
                'status': 'PASS' if result[0] > 0 else 'FAIL'
            }
            
            print(f"  ✓ Attributed {result[0]} channels")
            print(f"  ✓ Total credit: {result[1]:.2f}")
            print(f"  ✓ Conversions: {result[2]}")
    
    def test_strategic_plays(self):
        """Test strategic play execution."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(DISTINCT play_id) as plays,
                    SUM(touches) as total_touches,
                    SUM(conversions) as conversions
                FROM play_channel_attribution
                WHERE event_id = :eid
            """), {'eid': self.event_id}).fetchone()
            
            self.results['plays'] = {
                'plays_executed': result[0],
                'total_touches': result[1],
                'conversions': result[2],
                'status': 'PASS' if result[0] > 0 else 'FAIL'
            }
            
            print(f"  ✓ Executed {result[0]} strategic plays")
            print(f"  ✓ Total touches: {result[1]}")
            print(f"  ✓ Conversions: {result[2]}")
    
    def calculate_kpis(self):
        """Calculate key performance indicators."""
        
        # KPI 1: Conversion Rate
        conversion_rate = self.results['journeys']['conversion_rate']
        print(f"\n1. Conversion Rate: {conversion_rate*100:.1f}%")
        print(f"   Target: 30-50% | Status: {'✓ PASS' if conversion_rate >= 0.3 else '⚠ BELOW TARGET'}")
        
        # KPI 2: Revenue per Canvassing Hour
        # Assume: 10 doors/hour, avg deal = $15k
        conversions = self.results['journeys']['conversions']
        total_touches = self.results['plays']['total_touches']
        canvassing_hours = total_touches / 10  # 10 doors per hour
        revenue = conversions * 15000  # $15k avg deal
        revenue_per_hour = revenue / canvassing_hours if canvassing_hours > 0 else 0
        
        print(f"\n2. Revenue per Canvassing Hour: ${revenue_per_hour:,.0f}")
        print(f"   Target: $500-1000/hr | Status: {'✓ PASS' if revenue_per_hour >= 500 else '⚠ BELOW TARGET'}")
        
        # KPI 3: CAC (Customer Acquisition Cost)
        # Assume: $50/hour labor, $20/touch marketing
        labor_cost = canvassing_hours * 50
        marketing_cost = total_touches * 20
        total_cost = labor_cost + marketing_cost
        cac = total_cost / conversions if conversions > 0 else 0
        
        print(f"\n3. CAC (Customer Acquisition Cost): ${cac:,.0f}")
        print(f"   Target: <$2000 | Status: {'✓ PASS' if cac < 2000 else '⚠ ABOVE TARGET'}")
        
        # KPI 4: Attribution Quality
        attribution_credit = self.results['attribution']['total_credit']
        print(f"\n4. Attribution Quality: {attribution_credit:.2f}")
        print(f"   Target: ~1.0 (credit sums to 100%) | Status: {'✓ PASS' if 0.95 <= attribution_credit <= 1.05 else '⚠ CHECK'}")
        
        # KPI 5: SII_v2 Uplift
        avg_sii = self.results['sii_v2']['avg_score']
        print(f"\n5. Avg SII_v2 Score: {avg_sii:.2f}")
        print(f"   Target: >80 for A-tier | Status: {'✓ PASS' if avg_sii >= 80 else '⚠ BELOW TARGET'}")
        
        # Store KPIs
        self.results['kpis'] = {
            'conversion_rate': conversion_rate,
            'revenue_per_hour': revenue_per_hour,
            'cac': cac,
            'attribution_quality': attribution_credit,
            'avg_sii_v2': avg_sii
        }
    
    def save_results(self):
        """Save test results to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'e2e_test_{self.event_id}_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n✅ Results saved to {filename}")


if __name__ == '__main__':
    test = StormE2ETest('DFW_STORM_24')
    results = test.run_full_cycle()
    
    # Overall status
    print("\n" + "=" * 60)
    print("OVERALL STATUS")
    print("=" * 60)
    
    all_pass = all(
        phase['status'] == 'PASS' 
        for phase in results.values() 
        if isinstance(phase, dict) and 'status' in phase
    )
    
    if all_pass:
        print("✅ ALL PHASES PASSED")
        print("\nSystem ready for:")
        print("  • Scale to 4,200 roofs")
        print("  • Real team onboarding")
        print("  • Production deployment")
    else:
        print("⚠️  SOME PHASES NEED ATTENTION")
        print("\nReview failed/warned phases above")
