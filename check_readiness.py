#!/usr/bin/env python3
"""
Quick test to verify control plane is ready
"""

import os
import sys
from pathlib import Path

def check_file(path, description):
    """Check if file exists."""
    if Path(path).exists():
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ {description} - NOT FOUND")
        return False

def check_db_table(table_name):
    """Check if DB table exists."""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine('sqlite:///stormops_attribution.db')
        
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f"✅ Table '{table_name}' exists ({count} rows)")
            return True
    except Exception as e:
        print(f"❌ Table '{table_name}' - {str(e)}")
        return False

def main():
    print("=" * 60)
    print("StormOps Control Plane - Readiness Check")
    print("=" * 60)
    
    checks = []
    
    # Check files
    print("\nFiles:")
    checks.append(check_file("app.py", "UI app"))
    checks.append(check_file("policy_control_plane.py", "Policy engine"))
    checks.append(check_file("stormops_attribution.db", "Database"))
    checks.append(check_file("treatment_policy.py", "Treatment policy"))
    
    # Check DB tables
    print("\nDatabase Tables:")
    checks.append(check_db_table("customer_journeys"))
    checks.append(check_db_table("lead_uplift"))
    checks.append(check_db_table("experiment_assignments"))
    checks.append(check_db_table("treatment_decisions"))
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("\nReady to start:")
        print("  ./start_control_plane.sh")
        print("  OR")
        print("  streamlit run app.py")
        return 0
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total})")
        print("\nRun setup first:")
        print("  python3 e2e_storm_test.py")
        print("  python3 treatment_policy.py")
        return 1

if __name__ == '__main__':
    sys.exit(main())
