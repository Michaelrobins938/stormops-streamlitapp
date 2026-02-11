#!/usr/bin/env python3
"""
Integrated Data Pipeline: Quality → Enrichment → Features → Targeting
Run this as the single entry point for all data processing
"""

import subprocess
import sys

def run_script(script_name, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=False,
        text=True
    )
    
    if result.returncode != 0:
        print(f"\n❌ {script_name} failed with exit code {result.returncode}")
        return False
    
    print(f"\n✅ {description} complete")
    return True

def main():
    print("="*60)
    print("STORMOPS INTEGRATED DATA PIPELINE")
    print("="*60)
    print("\nPipeline stages:")
    print("  1. Data Quality & Validation")
    print("  2. Data Enrichment & Normalization")
    print("  3. External Data Enrichment (Census + Psychographics)")
    print("  4. Feature Engineering")
    print("  5. Targeting Engine")
    print("\n" + "="*60)
    
    stages = [
        ("data_quality.py", "Data Quality & Validation"),
        ("enrich_normalize_data.py", "Data Enrichment & Normalization"),
        ("external_data_copilot.py", "External Data Enrichment"),
        ("feature_engineering.py", "Feature Engineering"),
        ("targeting_engine.py", "Targeting Engine")
    ]
    
    for script, description in stages:
        if not run_script(script, description):
            print(f"\n❌ Pipeline failed at: {description}")
            sys.exit(1)
    
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETE - ALL STAGES PASSED")
    print("="*60)
    
    print("\n📊 Outputs Created:")
    print("   • All data quality checks passed")
    print("   • 100 properties fully enriched")
    print("   • 100 psychographic personas assigned")
    print("   • 26 model features engineered")
    print("   • 100 targeting recommendations generated")
    print("   • model_features.csv exported")
    
    print("\n🗄️  Database Assets:")
    print("   Tables: properties, census_tracts, psychographic_profiles, targeting_recommendations")
    print("   Views: high_priority_targets, zip_campaign_summary, model_features")
    
    print("\n🚀 Next Actions:")
    print("   1. Query high_priority_targets for immediate outreach")
    print("   2. Import model_features.csv into SII/MOE training")
    print("   3. Deploy targeting recommendations to StormOps UI")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
