#!/usr/bin/env python3
"""
Export enriched data for StormOps Control Plane UI
Prepares A-tier leads with full enrichment
"""

from sqlalchemy import create_engine, text
import pandas as pd
import json

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

def export_a_tier_leads(sii_threshold=70, risk_threshold=60):
    """Export A-tier leads for control plane"""
    print("\n🎯 Exporting A-Tier Leads for Control Plane")
    print("="*60)
    print(f"Criteria: SII ≥ {sii_threshold}, Risk ≥ {risk_threshold}")
    
    query = f"""
    SELECT 
        p.property_id,
        p.address,
        p.city,
        p.zip_code,
        p.estimated_value,
        p.square_footage,
        p.property_age,
        p.risk_score,
        p.price_per_sqft,
        
        -- Enrichment features
        p.insurance_burden_ratio,
        p.equity_risk_score,
        p.market_opportunity_score,
        p.physics_risk_score,
        p.hwds_exposure_score,
        
        -- Psychographic
        pp.primary_persona,
        pp.risk_tolerance,
        pp.price_sensitivity,
        
        -- Census/SES
        ct.median_household_income,
        ct.median_home_value,
        ct.homeownership_rate,
        
        -- Targeting
        tr.recommended_play,
        tr.sii_with_boost as sii_score,
        tr.follow_up_sla_hours,
        tr.play_message,
        
        -- Risk tier
        CASE 
            WHEN p.risk_score >= 80 THEN 'Very High'
            WHEN p.risk_score >= 60 THEN 'High'
            WHEN p.risk_score >= 40 THEN 'Medium'
            ELSE 'Low'
        END as risk_tier,
        
        -- Opportunity tier
        CASE 
            WHEN p.market_opportunity_score >= 80 
                 AND p.insurance_burden_ratio < 0.04 
                 AND p.equity_risk_score < 50 
            THEN 'High_Opportunity'
            WHEN p.market_opportunity_score >= 60 
            THEN 'Medium_Opportunity'
            ELSE 'Standard'
        END as opportunity_tier
        
    FROM properties p
    LEFT JOIN psychographic_profiles pp ON p.property_id = pp.property_id
    LEFT JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
    LEFT JOIN targeting_recommendations tr ON p.property_id::text = tr.property_id
    WHERE tr.sii_with_boost >= {sii_threshold}
      AND p.risk_score >= {risk_threshold}
    ORDER BY tr.sii_with_boost DESC, p.risk_score DESC
    """
    
    df = pd.read_sql(query, engine)
    
    print(f"\n✅ Exported {len(df)} A-tier leads")
    print(f"\n📊 Breakdown:")
    print(f"   Risk Tiers: {df['risk_tier'].value_counts().to_dict()}")
    print(f"   Personas: {df['primary_persona'].value_counts().to_dict()}")
    print(f"   Plays: {df['recommended_play'].value_counts().head(3).to_dict()}")
    
    # Export to CSV
    df.to_csv('a_tier_leads.csv', index=False)
    print(f"\n💾 Saved to: a_tier_leads.csv")
    
    # Export summary for UI
    summary = {
        'total_leads': len(df),
        'avg_sii': float(df['sii_score'].mean()),
        'avg_value': float(df['estimated_value'].mean()),
        'avg_risk': float(df['risk_score'].mean()),
        'risk_tiers': df['risk_tier'].value_counts().to_dict(),
        'personas': df['primary_persona'].value_counts().to_dict(),
        'top_plays': df['recommended_play'].value_counts().head(5).to_dict(),
        'opportunity_tiers': df['opportunity_tier'].value_counts().to_dict()
    }
    
    with open('a_tier_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"💾 Saved summary to: a_tier_summary.json")
    
    return df

def export_zip_summary():
    """Export ZIP-level summary for territory planning"""
    print("\n📍 Exporting ZIP Summary for Territory Planning")
    print("="*60)
    
    query = """
    SELECT 
        p.zip_code,
        COUNT(*) as property_count,
        ROUND(AVG(tr.sii_with_boost)) as avg_sii,
        ROUND(AVG(p.risk_score), 1) as avg_risk,
        ROUND(AVG(p.estimated_value)) as avg_value,
        ROUND(AVG(p.market_opportunity_score), 1) as avg_opportunity,
        MODE() WITHIN GROUP (ORDER BY pp.primary_persona) as dominant_persona,
        MODE() WITHIN GROUP (ORDER BY tr.recommended_play) as suggested_play,
        COUNT(*) FILTER (WHERE tr.sii_with_boost >= 90) as high_priority_count
    FROM properties p
    LEFT JOIN psychographic_profiles pp ON p.property_id = pp.property_id
    LEFT JOIN targeting_recommendations tr ON p.property_id::text = tr.property_id
    WHERE p.zip_code IS NOT NULL
    GROUP BY p.zip_code
    HAVING COUNT(*) >= 2
    ORDER BY avg_sii DESC
    """
    
    df = pd.read_sql(query, engine)
    
    print(f"✅ Exported {len(df)} ZIPs")
    
    df.to_csv('zip_summary.csv', index=False)
    print(f"💾 Saved to: zip_summary.csv")
    
    return df

def export_feature_stats():
    """Export feature statistics for validation"""
    print("\n📊 Exporting Feature Statistics")
    print("="*60)
    
    query = """
    SELECT 
        'estimated_value' as feature,
        COUNT(*) as count,
        ROUND(AVG(estimated_value)) as mean,
        ROUND(STDDEV(estimated_value)) as stddev,
        MIN(estimated_value) as min,
        MAX(estimated_value) as max
    FROM properties
    UNION ALL
    SELECT 
        'risk_score',
        COUNT(*),
        ROUND(AVG(risk_score), 1),
        ROUND(STDDEV(risk_score), 1),
        MIN(risk_score),
        MAX(risk_score)
    FROM properties
    UNION ALL
    SELECT 
        'insurance_burden_ratio',
        COUNT(*),
        ROUND(AVG(insurance_burden_ratio), 4),
        ROUND(STDDEV(insurance_burden_ratio), 4),
        MIN(insurance_burden_ratio),
        MAX(insurance_burden_ratio)
    FROM properties
    UNION ALL
    SELECT 
        'equity_risk_score',
        COUNT(*),
        ROUND(AVG(equity_risk_score), 1),
        ROUND(STDDEV(equity_risk_score), 1),
        MIN(equity_risk_score),
        MAX(equity_risk_score)
    FROM properties
    UNION ALL
    SELECT 
        'market_opportunity_score',
        COUNT(*),
        ROUND(AVG(market_opportunity_score), 1),
        ROUND(STDDEV(market_opportunity_score), 1),
        MIN(market_opportunity_score),
        MAX(market_opportunity_score)
    FROM properties
    """
    
    df = pd.read_sql(query, engine)
    
    print("\n📈 Feature Statistics:")
    print(df.to_string(index=False))
    
    df.to_csv('feature_stats.csv', index=False)
    print(f"\n💾 Saved to: feature_stats.csv")
    
    return df

def main():
    print("🚀 StormOps Control Plane Data Export")
    print("="*60)
    
    # Export A-tier leads
    a_tier = export_a_tier_leads(sii_threshold=70, risk_threshold=60)
    
    # Export ZIP summary
    zip_summary = export_zip_summary()
    
    # Export feature stats
    feature_stats = export_feature_stats()
    
    print("\n" + "="*60)
    print("✅ EXPORT COMPLETE")
    print("="*60)
    print("\nFiles created:")
    print("  • a_tier_leads.csv - Full lead data with enrichment")
    print("  • a_tier_summary.json - Summary for UI")
    print("  • zip_summary.csv - Territory planning data")
    print("  • feature_stats.csv - Feature validation stats")
    print("\n💡 Load these into the control plane UI at http://localhost:8501")

if __name__ == "__main__":
    main()
