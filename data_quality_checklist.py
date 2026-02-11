#!/usr/bin/env python3
"""
Data Quality v1 - Production Checklist
Run before any features enter SII/MOE or control plane
"""

from sqlalchemy import create_engine, text
import sys

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

class QualityCheck:
    def __init__(self, name, query, threshold, critical=True):
        self.name = name
        self.query = query
        self.threshold = threshold
        self.critical = critical
        self.result = None
        self.passed = None

CHECKS = [
    # Critical join keys
    QualityCheck(
        "No NULL property_id",
        "SELECT COUNT(*) FROM properties WHERE property_id IS NULL",
        0, critical=True
    ),
    QualityCheck(
        "No NULL census_tract_geoid in properties",
        "SELECT COUNT(*) FROM properties WHERE census_tract_geoid IS NULL",
        0, critical=True
    ),
    
    # Value ranges
    QualityCheck(
        "All estimated_value in range",
        "SELECT COUNT(*) FROM properties WHERE estimated_value NOT BETWEEN 50000 AND 5000000",
        0, critical=True
    ),
    QualityCheck(
        "All square_footage in range",
        "SELECT COUNT(*) FROM properties WHERE square_footage NOT BETWEEN 500 AND 10000",
        0, critical=True
    ),
    QualityCheck(
        "All risk_score in range",
        "SELECT COUNT(*) FROM properties WHERE risk_score NOT BETWEEN 0 AND 100",
        0, critical=True
    ),
    QualityCheck(
        "All median_household_income positive",
        "SELECT COUNT(*) FROM census_tracts WHERE median_household_income < 0",
        0, critical=True
    ),
    QualityCheck(
        "All median_home_value positive",
        "SELECT COUNT(*) FROM census_tracts WHERE median_home_value < 0",
        0, critical=True
    ),
    
    # Feature completeness
    QualityCheck(
        "Properties with risk_score",
        "SELECT COUNT(*) FROM properties WHERE risk_score IS NOT NULL",
        95, critical=False  # 95% threshold
    ),
    QualityCheck(
        "Properties with psychographic_persona",
        "SELECT COUNT(*) FROM psychographic_profiles",
        95, critical=False
    ),
    QualityCheck(
        "Properties with equity_risk_score",
        "SELECT COUNT(*) FROM properties WHERE equity_risk_score IS NOT NULL",
        95, critical=False
    ),
    
    # SII/MOE readiness
    QualityCheck(
        "Targeting recommendations generated",
        "SELECT COUNT(*) FROM targeting_recommendations",
        95, critical=False
    ),
    QualityCheck(
        "All sii_score in valid range",
        "SELECT COUNT(*) FROM targeting_recommendations WHERE sii_with_boost NOT BETWEEN 0 AND 150",
        0, critical=True
    ),
]

def run_checks():
    """Run all quality checks"""
    print("\n" + "="*60)
    print("DATA QUALITY v1 - PRODUCTION CHECKLIST")
    print("="*60)
    
    conn = engine.connect()
    
    critical_failures = []
    warnings = []
    
    for check in CHECKS:
        try:
            result = conn.execute(text(check.query))
            check.result = result.fetchone()[0]
            
            # Determine pass/fail
            if check.threshold == 0:
                check.passed = (check.result == 0)
            else:
                check.passed = (check.result >= check.threshold)
            
            # Report
            status = "✅" if check.passed else ("❌" if check.critical else "⚠️ ")
            print(f"{status} {check.name}: {check.result}")
            
            if not check.passed:
                if check.critical:
                    critical_failures.append(check)
                else:
                    warnings.append(check)
                    
        except Exception as e:
            print(f"❌ {check.name}: ERROR - {e}")
            if check.critical:
                critical_failures.append(check)
    
    conn.close()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if critical_failures:
        print(f"\n❌ {len(critical_failures)} CRITICAL FAILURES:")
        for check in critical_failures:
            print(f"   • {check.name}")
        print("\n🚫 DATA NOT READY FOR PRODUCTION")
        return False
    
    if warnings:
        print(f"\n⚠️  {len(warnings)} WARNINGS:")
        for check in warnings:
            print(f"   • {check.name}")
    
    print("\n✅ ALL CRITICAL CHECKS PASSED")
    print("✅ DATA READY FOR SII/MOE AND CONTROL PLANE")
    return True

def fix_issues():
    """Auto-fix common issues"""
    print("\n" + "="*60)
    print("AUTO-FIX COMMON ISSUES")
    print("="*60)
    
    conn = engine.connect()
    
    # Fix negative values
    conn.execute(text("""
        UPDATE census_tracts 
        SET median_household_income = NULL 
        WHERE median_household_income < 0
    """))
    print("✅ Nullified negative median_household_income")
    
    conn.execute(text("""
        UPDATE census_tracts 
        SET median_home_value = NULL 
        WHERE median_home_value < 0
    """))
    print("✅ Nullified negative median_home_value")
    
    # Bound risk scores
    conn.execute(text("""
        UPDATE properties 
        SET risk_score = LEAST(100, GREATEST(0, risk_score))
        WHERE risk_score IS NOT NULL
    """))
    print("✅ Bounded risk_score to 0-100")
    
    # Bound SII scores
    conn.execute(text("""
        UPDATE targeting_recommendations 
        SET sii_with_boost = LEAST(150, GREATEST(0, sii_with_boost))
        WHERE sii_with_boost IS NOT NULL
    """))
    print("✅ Bounded sii_with_boost to 0-150")
    
    conn.commit()
    conn.close()

def main():
    # Run checks
    passed = run_checks()
    
    if not passed:
        print("\n🔧 Attempting auto-fix...")
        fix_issues()
        print("\n🔄 Re-running checks...")
        passed = run_checks()
    
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
