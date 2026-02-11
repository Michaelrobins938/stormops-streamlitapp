"""
Production Pilot Storm Runner
Fully instrumented end-to-end storm execution with detailed reporting
"""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import uuid
import json
from typing import Dict
from policy_control_plane import PolicyControlPlane
from observability import DataObservability
import pandas as pd

class PilotStormRunner:
    """Run and instrument a production pilot storm."""
    
    def __init__(self, tenant_id: uuid.UUID, storm_id: uuid.UUID, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.tenant_id = tenant_id
        self.storm_id = storm_id
        self.engine = create_engine(db_url)
        self.pilot_id = uuid.uuid4()
        self.started_at = datetime.now()
        
    def run_pilot(self, policy_mode: str = 'moderate') -> Dict:
        """Execute full pilot storm with instrumentation."""
        
        print(f"🚀 Starting pilot storm: {self.storm_id}")
        print(f"   Tenant: {self.tenant_id}")
        print(f"   Policy: {policy_mode}")
        print(f"   Pilot ID: {self.pilot_id}")
        
        results = {
            'pilot_id': str(self.pilot_id),
            'tenant_id': str(self.tenant_id),
            'storm_id': str(self.storm_id),
            'policy_mode': policy_mode,
            'started_at': self.started_at.isoformat()
        }
        
        # Phase 1: Apply policy
        print("\n📋 Phase 1: Applying treatment policy...")
        policy_result = self._apply_policy(policy_mode)
        results['policy'] = policy_result
        
        # Phase 2: Pre-storm baseline
        print("\n📊 Phase 2: Capturing baseline metrics...")
        baseline = self._capture_baseline()
        results['baseline'] = baseline
        
        # Phase 3: Storm execution (simulated for pilot)
        print("\n⚡ Phase 3: Storm execution...")
        execution = self._execute_storm()
        results['execution'] = execution
        
        # Phase 4: Measure outcomes
        print("\n📈 Phase 4: Measuring outcomes...")
        outcomes = self._measure_outcomes()
        results['outcomes'] = outcomes
        
        # Phase 5: Calculate ROI
        print("\n💰 Phase 5: Calculating ROI...")
        roi = self._calculate_roi(outcomes)
        results['roi'] = roi
        
        # Phase 6: Data quality checks
        print("\n🔍 Phase 6: Data quality checks...")
        quality = self._check_data_quality()
        results['quality'] = quality
        
        # Save pilot report
        self._save_pilot_report(results)
        
        results['completed_at'] = datetime.now().isoformat()
        results['duration_minutes'] = (datetime.now() - self.started_at).total_seconds() / 60
        
        return results
    
    def _apply_policy(self, policy_mode: str) -> Dict:
        """Apply treatment policy."""
        plane = PolicyControlPlane(policy_mode=policy_mode)
        result = plane.apply_policy(str(self.storm_id))
        
        return {
            'treat_count': result['treat'],
            'hold_count': result['hold'],
            'treat_pct': result['treat_pct'],
            'execution_id': result['execution_id']
        }
    
    def _capture_baseline(self) -> Dict:
        """Capture pre-storm baseline metrics."""
        obs = DataObservability(self.tenant_id)
        
        # Uplift distribution
        dist = obs.check_uplift_distribution(self.storm_id)
        
        # Property counts
        with self.engine.connect() as conn:
            conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': self.tenant_id})
            
            prop_count = conn.execute(text("""
                SELECT COUNT(*) FROM properties WHERE tenant_id = :tid
            """), {'tid': self.tenant_id}).scalar()
        
        return {
            'properties': prop_count,
            'uplift_mean': dist.get('mean'),
            'uplift_stddev': dist.get('stddev'),
            'drift_detected': dist.get('drift_detected', False)
        }
    
    def _execute_storm(self) -> Dict:
        """Execute storm (log touches)."""
        # In production, this would track actual field operations
        # For pilot, we simulate based on policy decisions
        
        with self.engine.connect() as conn:
            conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': self.tenant_id})
            
            # Count properties by decision
            decisions = conn.execute(text("""
                SELECT decision, COUNT(*) as count
                FROM policy_decisions_log
                WHERE tenant_id = :tid AND storm_id = :sid
                GROUP BY decision
            """), {'tid': self.tenant_id, 'sid': self.storm_id}).fetchall()
        
        return {
            'decisions': {d[0]: d[1] for d in decisions},
            'execution_time': datetime.now().isoformat()
        }
    
    def _measure_outcomes(self) -> Dict:
        """Measure actual outcomes."""
        
        with self.engine.connect() as conn:
            conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': self.tenant_id})
            
            # Get outcomes by decision
            outcomes = conn.execute(text("""
                SELECT 
                    decision,
                    COUNT(*) as n,
                    SUM(CASE WHEN actual_converted THEN 1 ELSE 0 END) as conversions,
                    AVG(CASE WHEN actual_converted THEN 1.0 ELSE 0.0 END) as rate,
                    SUM(conversion_value) as revenue
                FROM policy_outcomes
                WHERE tenant_id = :tid AND storm_id = :sid
                GROUP BY decision
            """), {'tid': self.tenant_id, 'sid': self.storm_id}).fetchall()
        
        result = {}
        for row in outcomes:
            result[row[0]] = {
                'n': row[1],
                'conversions': row[2],
                'rate': float(row[3]),
                'revenue': float(row[4]) if row[4] else 0
            }
        
        # Calculate lift
        if 'treat' in result and 'hold' in result:
            lift = result['treat']['rate'] - result['hold']['rate']
            result['lift'] = {
                'absolute': lift,
                'relative': (lift / result['hold']['rate'] * 100) if result['hold']['rate'] > 0 else 0
            }
        
        return result
    
    def _calculate_roi(self, outcomes: Dict) -> Dict:
        """Calculate ROI metrics."""
        
        if 'treat' not in outcomes or 'hold' not in outcomes:
            return {'error': 'Insufficient data for ROI calculation'}
        
        treat = outcomes['treat']
        hold = outcomes['hold']
        
        # Costs (assume $50 per property treated)
        cost_per_property = 50
        total_cost = treat['n'] * cost_per_property
        
        # Revenue
        treat_revenue = treat['revenue']
        
        # Incremental revenue (vs if we hadn't treated)
        baseline_revenue = treat['n'] * hold['rate'] * 15000  # Assume $15k per conversion
        incremental_revenue = treat_revenue - baseline_revenue
        
        # ROI
        roi = (incremental_revenue - total_cost) / total_cost if total_cost > 0 else 0
        
        # CAC
        cac = total_cost / treat['conversions'] if treat['conversions'] > 0 else 0
        
        # Revenue per hour (assume 7-day storm)
        revenue_per_hour = treat_revenue / (7 * 24)
        
        return {
            'total_cost': total_cost,
            'treat_revenue': treat_revenue,
            'baseline_revenue': baseline_revenue,
            'incremental_revenue': incremental_revenue,
            'roi': roi,
            'roi_pct': roi * 100,
            'cac': cac,
            'revenue_per_hour': revenue_per_hour
        }
    
    def _check_data_quality(self) -> Dict:
        """Run data quality checks."""
        obs = DataObservability(self.tenant_id)
        dashboard = obs.get_health_dashboard(self.storm_id)
        
        return {
            'health_status': dashboard['health_status'],
            'issues': dashboard['issues'],
            'uplift_drift': dashboard['uplift_distribution'].get('drift_detected', False),
            'conversion_anomaly': dashboard['conversion_rates'].get('anomaly', False)
        }
    
    def _save_pilot_report(self, results: Dict):
        """Save pilot report to database."""
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pilot_storm_reports (
                    pilot_id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    storm_id UUID NOT NULL,
                    policy_mode TEXT NOT NULL,
                    results JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            
            conn.execute(text("""
                INSERT INTO pilot_storm_reports (pilot_id, tenant_id, storm_id, policy_mode, results)
                VALUES (:pid, :tid, :sid, :mode, :results)
            """), {
                'pid': self.pilot_id,
                'tid': self.tenant_id,
                'sid': self.storm_id,
                'mode': results['policy_mode'],
                'results': json.dumps(results)
            })
    
    def generate_report_pdf(self, results: Dict, output_path: str = 'pilot_storm_report.md'):
        """Generate markdown report (convert to PDF with pandoc)."""
        
        report = f"""# Pilot Storm Report

**Tenant:** {results['tenant_id']}
**Storm:** {results['storm_id']}
**Policy:** {results['policy_mode']}
**Date:** {results['started_at']}
**Duration:** {results['duration_minutes']:.1f} minutes

---

## Executive Summary

### Treatment Policy
- **Treated:** {results['policy']['treat_count']} properties ({results['policy']['treat_pct']:.1f}%)
- **Held Out:** {results['policy']['hold_count']} properties

### Results
- **Treatment Conversion:** {results['outcomes']['treat']['rate']*100:.1f}%
- **Control Conversion:** {results['outcomes']['hold']['rate']*100:.1f}%
- **Lift:** {results['outcomes']['lift']['absolute']*100:+.1f} pts ({results['outcomes']['lift']['relative']:+.1f}%)

### ROI
- **Total Cost:** ${results['roi']['total_cost']:,.0f}
- **Revenue:** ${results['roi']['treat_revenue']:,.0f}
- **Incremental Revenue:** ${results['roi']['incremental_revenue']:,.0f}
- **ROI:** {results['roi']['roi_pct']:.1f}%
- **CAC:** ${results['roi']['cac']:.0f}
- **Revenue/Hour:** ${results['roi']['revenue_per_hour']:.0f}

---

## Baseline Metrics

- **Properties:** {results['baseline']['properties']}
- **Uplift Mean:** {results['baseline']['uplift_mean']:.3f}
- **Uplift Stddev:** {results['baseline']['uplift_stddev']:.3f}
- **Drift Detected:** {'Yes ⚠️' if results['baseline']['drift_detected'] else 'No ✅'}

---

## Outcomes by Decision

### Treatment Group
- **N:** {results['outcomes']['treat']['n']}
- **Conversions:** {results['outcomes']['treat']['conversions']}
- **Rate:** {results['outcomes']['treat']['rate']*100:.1f}%
- **Revenue:** ${results['outcomes']['treat']['revenue']:,.0f}

### Control Group
- **N:** {results['outcomes']['hold']['n']}
- **Conversions:** {results['outcomes']['hold']['conversions']}
- **Rate:** {results['outcomes']['hold']['rate']*100:.1f}%
- **Revenue:** ${results['outcomes']['hold']['revenue']:,.0f}

---

## Data Quality

- **Health Status:** {results['quality']['health_status']}
- **Issues:** {', '.join(results['quality']['issues']) if results['quality']['issues'] else 'None'}
- **Uplift Drift:** {'Detected ⚠️' if results['quality']['uplift_drift'] else 'None ✅'}
- **Conversion Anomaly:** {'Detected ⚠️' if results['quality']['conversion_anomaly'] else 'None ✅'}

---

## Recommendations

{'✅ **Success:** Lift exceeds 10 pts, ROI > 300%. Ready to scale.' if results['outcomes']['lift']['absolute'] > 0.10 and results['roi']['roi'] > 3.0 else '⚠️ **Review:** Lift or ROI below target. Review policy and data quality.'}

---

**Report Generated:** {datetime.now().isoformat()}
"""
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Report saved: {output_path}")
        print(f"   Convert to PDF: pandoc {output_path} -o pilot_storm_report.pdf")


if __name__ == '__main__':
    print("=" * 60)
    print("PRODUCTION PILOT STORM RUNNER")
    print("=" * 60)
    
    # Example: Run pilot for DFW Elite Roofing
    tenant_id = uuid.UUID('00000000-0000-0000-0000-000000000000')  # Replace with real tenant
    storm_id = uuid.uuid4()  # Replace with real storm
    
    runner = PilotStormRunner(tenant_id, storm_id)
    results = runner.run_pilot(policy_mode='moderate')
    
    print("\n" + "=" * 60)
    print("PILOT COMPLETE")
    print("=" * 60)
    
    print(f"\n📊 Results:")
    print(f"   Treat: {results['policy']['treat_count']} ({results['policy']['treat_pct']:.1f}%)")
    print(f"   Lift: {results['outcomes']['lift']['absolute']*100:+.1f} pts")
    print(f"   ROI: {results['roi']['roi_pct']:.1f}%")
    print(f"   Incremental Revenue: ${results['roi']['incremental_revenue']:,.0f}")
    
    # Generate report
    runner.generate_report_pdf(results)
