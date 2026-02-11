#!/usr/bin/env python3
"""
Advanced Data Ingestion Plan: Insurance Economics + Hazard Physics
Priority sources: FHFA mortgage data, Texas DOI insurance data, CLIMADA hail model
"""

from sqlalchemy import create_engine, text
import pandas as pd
import requests
from datetime import datetime

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

# ============================================================================
# DATA SOURCE 1: FHFA Mortgage & Appraisal Data
# ============================================================================

def ingest_fhfa_mortgage_data():
    """
    FHFA House Price Index (HPI) and Mortgage Data by Census Tract
    
    Source: https://www.fhfa.gov/data/datasets
    Key datasets:
    - Census Tract HPI (quarterly)
    - Loan-to-Value ratios by tract
    - Underserved area flags
    
    Features added:
    - hpi_index: House price index (baseline 100)
    - hpi_yoy_change: Year-over-year price change %
    - avg_ltv: Average loan-to-value ratio
    - underserved_flag: HUD underserved area designation
    - equity_estimate: Estimated equity position
    """
    print("\n📊 FHFA Mortgage & Appraisal Data")
    print("=" * 60)
    
    conn = engine.connect()
    
    # Create FHFA data table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS fhfa_tract_data (
            tract_geoid TEXT PRIMARY KEY,
            hpi_index DECIMAL(10,2),
            hpi_yoy_change DECIMAL(5,2),
            avg_ltv DECIMAL(5,2),
            avg_appraisal_value INTEGER,
            underserved_flag BOOLEAN,
            equity_estimate DECIMAL(5,2),
            data_date DATE,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """))
    
    # TODO: Actual API integration
    # For now, create synthetic data structure
    print("  📥 Data structure created")
    print("  🔗 API endpoint: https://www.fhfa.gov/DataTools/Downloads/Pages/HPI.aspx")
    print("  📋 Fields: HPI index, LTV ratios, underserved flags")
    
    conn.commit()
    conn.close()
    
    return {
        'table': 'fhfa_tract_data',
        'join_key': 'tract_geoid',
        'features': ['hpi_index', 'hpi_yoy_change', 'avg_ltv', 'equity_estimate', 'underserved_flag'],
        'use_cases': [
            'Refine affordability scoring',
            'Predict "repair vs walk" likelihood',
            'Segment by equity position',
            'Adjust MOE priors by leverage'
        ]
    }

# ============================================================================
# DATA SOURCE 2: Texas Department of Insurance (TDI) Market Data
# ============================================================================

def ingest_tdi_insurance_data():
    """
    Texas DOI Property & Casualty Market Reports
    
    Source: https://www.tdi.texas.gov/reports/report4.html
    Key datasets:
    - ZIP-level premium, loss, expense by line
    - Residential property loss ratios
    - Carrier market share
    
    Features added:
    - hail_loss_ratio: Historical hail loss ratio
    - property_loss_frequency: Claims per 1000 policies
    - avg_premium: Average annual premium
    - carrier_concentration: HHI index
    - market_competitiveness: Carrier count
    """
    print("\n🏢 Texas DOI Insurance Market Data")
    print("=" * 60)
    
    conn = engine.connect()
    
    # Create TDI data table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tdi_zip_insurance (
            zip_code TEXT PRIMARY KEY,
            hail_loss_ratio DECIMAL(5,2),
            property_loss_frequency DECIMAL(8,2),
            avg_premium INTEGER,
            total_exposure BIGINT,
            carrier_concentration DECIMAL(5,2),
            market_competitiveness INTEGER,
            data_year INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """))
    
    print("  📥 Data structure created")
    print("  🔗 Source: TDI P&C Exhibit Reports")
    print("  📋 Fields: Loss ratios, premiums, carrier metrics")
    
    conn.commit()
    conn.close()
    
    return {
        'table': 'tdi_zip_insurance',
        'join_key': 'zip_code',
        'features': ['hail_loss_ratio', 'property_loss_frequency', 'avg_premium', 'carrier_concentration'],
        'use_cases': [
            'Add "historical hail severity" to risk scoring',
            'Identify high-opportunity ZIPs (high loss + competition)',
            'Adjust play aggressiveness by market dynamics',
            'Price sensitivity by premium burden'
        ]
    }

# ============================================================================
# DATA SOURCE 3: CLIMADA Hail Damage Model
# ============================================================================

def ingest_climada_hazard_data():
    """
    CLIMADA Open-Source Hail Damage Model
    
    Source: https://nhess.copernicus.org/articles/24/847/2024/
    Key datasets:
    - 250k geolocated hail damage reports
    - MESHS-based hazard intensity fields
    - Calibrated damage functions
    
    Features added:
    - climada_hail_hazard: Modeled hail hazard intensity
    - historical_hail_events: Event count (10yr)
    - max_meshs_observed: Maximum MESHS recorded
    - damage_probability: Calibrated damage probability
    """
    print("\n⛈️  CLIMADA Hail Hazard Model")
    print("=" * 60)
    
    conn = engine.connect()
    
    # Create CLIMADA hazard table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS climada_hail_hazard (
            location_id SERIAL PRIMARY KEY,
            latitude DECIMAL(10,8),
            longitude DECIMAL(11,8),
            tract_geoid TEXT,
            zip_code TEXT,
            climada_hail_hazard DECIMAL(5,2),
            historical_hail_events INTEGER,
            max_meshs_observed DECIMAL(5,1),
            damage_probability DECIMAL(5,4),
            return_period_10yr DECIMAL(5,2),
            return_period_50yr DECIMAL(5,2),
            data_date DATE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_climada_tract ON climada_hail_hazard(tract_geoid);
        CREATE INDEX IF NOT EXISTS idx_climada_zip ON climada_hail_hazard(zip_code);
    """))
    
    print("  📥 Data structure created")
    print("  🔗 Source: CLIMADA open hail model")
    print("  📋 Fields: Hazard intensity, event frequency, damage probability")
    
    conn.commit()
    conn.close()
    
    return {
        'table': 'climada_hail_hazard',
        'join_key': 'tract_geoid OR zip_code',
        'features': ['climada_hail_hazard', 'historical_hail_events', 'damage_probability', 'return_period_10yr'],
        'use_cases': [
            'Cross-validate NOAA storm triggers',
            'Independent hazard scoring for SII',
            'Long-term market selection (return periods)',
            'Calibrate MOE with physics-based damage functions'
        ]
    }

# ============================================================================
# INTEGRATION: Enhanced Risk & Opportunity Scoring
# ============================================================================

def create_enhanced_risk_view():
    """
    Create integrated view combining all new data sources
    """
    print("\n🔧 Creating Enhanced Risk & Opportunity View")
    print("=" * 60)
    
    conn = engine.connect()
    
    conn.execute(text("""
        CREATE OR REPLACE VIEW enhanced_risk_scoring AS
        SELECT 
            p.property_id,
            p.address,
            p.city,
            p.zip_code,
            p.census_tract_geoid,
            
            -- Existing risk factors
            p.risk_score as base_risk_score,
            p.property_age,
            p.estimated_value,
            
            -- FHFA mortgage context
            fhfa.hpi_index,
            fhfa.hpi_yoy_change,
            fhfa.avg_ltv,
            fhfa.equity_estimate,
            fhfa.underserved_flag,
            
            -- TDI insurance market
            tdi.hail_loss_ratio,
            tdi.property_loss_frequency,
            tdi.avg_premium,
            tdi.carrier_concentration,
            tdi.market_competitiveness,
            
            -- CLIMADA hazard physics
            ch.climada_hail_hazard,
            ch.historical_hail_events,
            ch.damage_probability,
            ch.return_period_10yr,
            
            -- Psychographic context
            pp.primary_persona,
            pp.price_sensitivity,
            pp.risk_tolerance,
            
            -- Derived opportunity score
            CASE 
                WHEN tdi.hail_loss_ratio > 0.8 
                     AND tdi.market_competitiveness >= 5 
                     AND fhfa.equity_estimate > 0.2
                THEN 'High_Opportunity'
                WHEN tdi.hail_loss_ratio > 0.6 
                     AND fhfa.equity_estimate > 0.1
                THEN 'Medium_Opportunity'
                ELSE 'Standard'
            END as opportunity_tier
            
        FROM properties p
        LEFT JOIN fhfa_tract_data fhfa ON p.census_tract_geoid = fhfa.tract_geoid
        LEFT JOIN tdi_zip_insurance tdi ON p.zip_code = tdi.zip_code
        LEFT JOIN climada_hail_hazard ch ON p.census_tract_geoid = ch.tract_geoid
        LEFT JOIN psychographic_profiles pp ON p.property_id = pp.property_id;
    """))
    
    print("  ✅ Created enhanced_risk_scoring view")
    print("  📊 Combines: FHFA + TDI + CLIMADA + existing data")
    
    conn.commit()
    conn.close()

# ============================================================================
# FEATURE ENGINEERING: Insurance Economics Features
# ============================================================================

def engineer_insurance_features():
    """
    Create derived features from insurance economics data
    """
    print("\n🔬 Engineering Insurance Economics Features")
    print("=" * 60)
    
    conn = engine.connect()
    
    # Add feature columns
    conn.execute(text("""
        ALTER TABLE properties 
        ADD COLUMN IF NOT EXISTS insurance_burden_ratio DECIMAL(5,4),
        ADD COLUMN IF NOT EXISTS equity_risk_score DECIMAL(5,2),
        ADD COLUMN IF NOT EXISTS market_opportunity_score DECIMAL(5,2),
        ADD COLUMN IF NOT EXISTS physics_risk_score DECIMAL(5,2);
    """))
    
    # Calculate insurance burden (premium / income)
    conn.execute(text("""
        UPDATE properties p
        SET insurance_burden_ratio = tdi.avg_premium::DECIMAL / NULLIF(ct.median_household_income, 0)
        FROM tdi_zip_insurance tdi, census_tracts ct
        WHERE p.zip_code = tdi.zip_code
          AND p.census_tract_geoid = ct.tract_geoid
          AND tdi.avg_premium IS NOT NULL
          AND ct.median_household_income > 0;
    """))
    
    # Calculate equity risk (LTV-based)
    conn.execute(text("""
        UPDATE properties p
        SET equity_risk_score = 
            CASE 
                WHEN fhfa.avg_ltv > 0.9 THEN 90
                WHEN fhfa.avg_ltv > 0.8 THEN 70
                WHEN fhfa.avg_ltv > 0.7 THEN 50
                WHEN fhfa.avg_ltv > 0.6 THEN 30
                ELSE 10
            END
        FROM fhfa_tract_data fhfa
        WHERE p.census_tract_geoid = fhfa.tract_geoid
          AND fhfa.avg_ltv IS NOT NULL;
    """))
    
    # Calculate market opportunity (loss ratio + competition)
    conn.execute(text("""
        UPDATE properties p
        SET market_opportunity_score = 
            LEAST(100, GREATEST(0,
                (tdi.hail_loss_ratio * 50) + 
                (tdi.market_competitiveness * 5) +
                CASE WHEN tdi.carrier_concentration < 0.3 THEN 20 ELSE 0 END
            ))
        FROM tdi_zip_insurance tdi
        WHERE p.zip_code = tdi.zip_code
          AND tdi.hail_loss_ratio IS NOT NULL;
    """))
    
    # Calculate physics risk (CLIMADA-based)
    conn.execute(text("""
        UPDATE properties p
        SET physics_risk_score = 
            LEAST(100, GREATEST(0,
                (ch.damage_probability * 100) +
                (ch.historical_hail_events * 2) +
                CASE WHEN ch.return_period_10yr > 50 THEN 20 ELSE 0 END
            ))
        FROM climada_hail_hazard ch
        WHERE p.census_tract_geoid = ch.tract_geoid
          AND ch.damage_probability IS NOT NULL;
    """))
    
    print("  ✅ Created insurance_burden_ratio")
    print("  ✅ Created equity_risk_score")
    print("  ✅ Created market_opportunity_score")
    print("  ✅ Created physics_risk_score")
    
    conn.commit()
    conn.close()

# ============================================================================
# INGESTION PLAN SUMMARY
# ============================================================================

def generate_ingestion_plan():
    """
    Generate complete ingestion plan and next steps
    """
    print("\n" + "=" * 60)
    print("📋 ADVANCED DATA INGESTION PLAN")
    print("=" * 60)
    
    sources = [
        ingest_fhfa_mortgage_data(),
        ingest_tdi_insurance_data(),
        ingest_climada_hazard_data()
    ]
    
    create_enhanced_risk_view()
    engineer_insurance_features()
    
    print("\n" + "=" * 60)
    print("✅ INGESTION PLAN COMPLETE")
    print("=" * 60)
    
    print("\n📊 Data Sources Configured:")
    for i, source in enumerate(sources, 1):
        print(f"\n{i}. {source['table']}")
        print(f"   Join: {source['join_key']}")
        print(f"   Features: {', '.join(source['features'][:3])}...")
        print(f"   Use cases:")
        for uc in source['use_cases'][:2]:
            print(f"     • {uc}")
    
    print("\n🔧 New Features Engineered:")
    print("   • insurance_burden_ratio - Premium / income")
    print("   • equity_risk_score - LTV-based risk (0-100)")
    print("   • market_opportunity_score - Loss ratio + competition")
    print("   • physics_risk_score - CLIMADA damage probability")
    
    print("\n📋 New Views Created:")
    print("   • enhanced_risk_scoring - All sources integrated")
    
    print("\n🚀 Next Steps:")
    print("\n1. DATA ACQUISITION:")
    print("   a. FHFA: Download Census Tract HPI data")
    print("      → https://www.fhfa.gov/DataTools/Downloads/Pages/HPI.aspx")
    print("      → Parse CSV, load to fhfa_tract_data")
    print("   ")
    print("   b. TDI: Download P&C Exhibit Reports (Texas)")
    print("      → https://www.tdi.texas.gov/reports/report4.html")
    print("      → Extract ZIP-level loss ratios, load to tdi_zip_insurance")
    print("   ")
    print("   c. CLIMADA: Clone repo, run hail model")
    print("      → https://github.com/CLIMADA-project/climada_python")
    print("      → Generate hazard maps for Dallas County")
    print("      → Load to climada_hail_hazard")
    
    print("\n2. MODEL INTEGRATION:")
    print("   • Add 4 new features to SII model:")
    print("     - insurance_burden_ratio")
    print("     - equity_risk_score")
    print("     - market_opportunity_score")
    print("     - physics_risk_score")
    print("   ")
    print("   • Update MOE priors by equity position:")
    print("     - High equity (LTV < 0.6): Lower MOE")
    print("     - Low equity (LTV > 0.8): Higher MOE")
    print("   ")
    print("   • Adjust play selection by opportunity tier:")
    print("     - High_Opportunity: More aggressive plays")
    print("     - Standard: Current playbook")
    
    print("\n3. TARGETING REFINEMENT:")
    print("   • Query high-opportunity properties:")
    print("     SELECT * FROM enhanced_risk_scoring")
    print("     WHERE opportunity_tier = 'High_Opportunity'")
    print("       AND physics_risk_score > 60;")
    print("   ")
    print("   • Segment campaigns by insurance burden:")
    print("     - High burden: Emphasize savings, efficiency")
    print("     - Low burden: Emphasize quality, protection")
    
    print("\n4. VALIDATION:")
    print("   • Cross-validate CLIMADA vs NOAA storm triggers")
    print("   • Compare TDI loss ratios to actual claim rates")
    print("   • SHAP analysis on new features")
    
    print("\n" + "=" * 60)

def main():
    print("🚀 Advanced Data Ingestion: Insurance Economics + Hazard Physics")
    print("=" * 60)
    
    try:
        generate_ingestion_plan()
        
        print("\n💡 Implementation Priority:")
        print("   1. TDI data (easiest, immediate impact on targeting)")
        print("   2. FHFA data (moderate effort, refines affordability)")
        print("   3. CLIMADA model (complex, but best physics validation)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
