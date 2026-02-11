#!/usr/bin/env python3
"""
Targeting Engine - Micro-play recommendations based on enriched property graph
"""

from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

# Play definitions based on persona + risk combinations
PLAY_MATRIX = {
    ('Proof_Seeker', 'Very High'): {
        'play': 'Impact_Report_Premium',
        'message': 'Physics-grade damage assessment with adjuster documentation',
        'sii_boost': 25,
        'materials': ['premium_shingles', 'impact_resistant'],
        'follow_up_sla_hours': 24
    },
    ('Proof_Seeker', 'High'): {
        'play': 'Impact_Report_Standard',
        'message': 'Detailed damage report with photo documentation',
        'sii_boost': 20,
        'materials': ['premium_shingles'],
        'follow_up_sla_hours': 48
    },
    ('Deal_Hunter', 'Very High'): {
        'play': 'Financing_Aggressive',
        'message': '0% financing + free inspection + price match guarantee',
        'sii_boost': 30,
        'materials': ['value_shingles', 'standard'],
        'follow_up_sla_hours': 12
    },
    ('Deal_Hunter', 'High'): {
        'play': 'Financing_Standard',
        'message': 'Low-rate financing + competitive pricing',
        'sii_boost': 20,
        'materials': ['value_shingles'],
        'follow_up_sla_hours': 24
    },
    ('Deal_Hunter', 'Medium'): {
        'play': 'Promo_Seasonal',
        'message': 'Seasonal discount + bundled services',
        'sii_boost': 15,
        'materials': ['standard'],
        'follow_up_sla_hours': 48
    },
    ('Family_Protector', 'Very High'): {
        'play': 'Safety_Warranty',
        'message': 'Extended warranty + safety inspection + family protection focus',
        'sii_boost': 25,
        'materials': ['premium_shingles', 'impact_resistant'],
        'follow_up_sla_hours': 24
    },
    ('Family_Protector', 'High'): {
        'play': 'Safety_Standard',
        'message': 'Warranty + safety focus + reliable materials',
        'sii_boost': 18,
        'materials': ['standard', 'premium_shingles'],
        'follow_up_sla_hours': 36
    },
    ('Family_Protector', 'Medium'): {
        'play': 'Reliability_Focus',
        'message': 'Proven materials + solid warranty',
        'sii_boost': 12,
        'materials': ['standard'],
        'follow_up_sla_hours': 48
    },
    ('Status_Conscious', 'Very High'): {
        'play': 'Premium_Showcase',
        'message': 'Designer materials + curb appeal + neighborhood showcase',
        'sii_boost': 28,
        'materials': ['designer', 'premium_shingles'],
        'follow_up_sla_hours': 24
    },
    ('Status_Conscious', 'High'): {
        'play': 'Premium_Standard',
        'message': 'High-end materials + aesthetic focus',
        'sii_boost': 22,
        'materials': ['premium_shingles'],
        'follow_up_sla_hours': 36
    },
}

def get_risk_category(score):
    if score < 40: return 'Low'
    if score < 60: return 'Medium'
    if score < 80: return 'High'
    return 'Very High'

def generate_targeting_recommendations():
    """Generate play recommendations for all properties"""
    print("\n🎯 Generating Targeting Recommendations")
    print("=" * 60)
    
    query = """
    SELECT 
        p.property_id,
        p.address,
        p.city,
        p.zip_code,
        p.estimated_value,
        p.risk_score,
        pp.primary_persona,
        pp.risk_tolerance,
        pp.price_sensitivity,
        ct.median_household_income,
        ct.affordability_index
    FROM properties p
    JOIN psychographic_profiles pp ON p.property_id = pp.property_id
    LEFT JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
    WHERE p.risk_score IS NOT NULL
    """
    
    df = pd.read_sql(query, engine)
    df['risk_category'] = df['risk_score'].apply(get_risk_category)
    
    # Generate play recommendations
    recommendations = []
    for _, row in df.iterrows():
        key = (row['primary_persona'], row['risk_category'])
        play = PLAY_MATRIX.get(key, {
            'play': 'Standard_Outreach',
            'message': 'General roofing services',
            'sii_boost': 10,
            'materials': ['standard'],
            'follow_up_sla_hours': 72
        })
        
        # Calculate base SII (simplified)
        base_sii = 50
        if row['risk_score'] > 70: base_sii += 20
        if row['estimated_value'] > 350000: base_sii += 10
        
        recommendations.append({
            'property_id': row['property_id'],
            'address': row['address'],
            'city': row['city'],
            'zip_code': row['zip_code'],
            'persona': row['primary_persona'],
            'risk_category': row['risk_category'],
            'risk_score': row['risk_score'],
            'estimated_value': row['estimated_value'],
            'recommended_play': play['play'],
            'play_message': play['message'],
            'base_sii': base_sii,
            'sii_with_boost': base_sii + play['sii_boost'],
            'materials': ','.join(play['materials']),
            'follow_up_sla_hours': play['follow_up_sla_hours'],
            'price_sensitivity': row['price_sensitivity'],
            'risk_tolerance': row['risk_tolerance']
        })
    
    rec_df = pd.DataFrame(recommendations)
    
    # Save to database
    conn = engine.connect()
    conn.execute(text("DROP TABLE IF EXISTS targeting_recommendations CASCADE"))
    conn.commit()
    
    rec_df.to_sql('targeting_recommendations', engine, if_exists='replace', index=False)
    
    print(f"✅ Generated {len(rec_df)} recommendations")
    
    # Summary by play
    print("\n📊 Play Distribution:")
    play_summary = rec_df.groupby('recommended_play').agg({
        'property_id': 'count',
        'sii_with_boost': 'mean',
        'estimated_value': 'mean'
    }).round(0)
    play_summary.columns = ['count', 'avg_sii', 'avg_value']
    print(play_summary.sort_values('count', ascending=False).to_string())
    
    conn.close()
    return rec_df

def create_operator_views():
    """Create operator-facing views for StormOps UI"""
    print("\n📋 Creating Operator Views")
    print("=" * 60)
    
    conn = engine.connect()
    
    # High-priority targets
    conn.execute(text("""
        CREATE OR REPLACE VIEW high_priority_targets AS
        SELECT 
            property_id,
            address,
            city,
            zip_code,
            persona,
            risk_category,
            risk_score,
            recommended_play,
            play_message,
            sii_with_boost as priority_score,
            follow_up_sla_hours,
            materials
        FROM targeting_recommendations
        WHERE sii_with_boost >= 70
        ORDER BY sii_with_boost DESC, follow_up_sla_hours ASC;
    """))
    
    # Financing campaign targets
    conn.execute(text("""
        CREATE OR REPLACE VIEW financing_campaign_targets AS
        SELECT 
            property_id,
            address,
            city,
            zip_code,
            persona,
            risk_score,
            estimated_value,
            price_sensitivity,
            recommended_play,
            play_message
        FROM targeting_recommendations
        WHERE persona = 'Deal_Hunter'
          AND price_sensitivity > 60
        ORDER BY price_sensitivity DESC, risk_score DESC;
    """))
    
    # Premium upsell targets
    conn.execute(text("""
        CREATE OR REPLACE VIEW premium_upsell_targets AS
        SELECT 
            property_id,
            address,
            city,
            zip_code,
            persona,
            estimated_value,
            risk_tolerance,
            recommended_play,
            materials
        FROM targeting_recommendations
        WHERE persona IN ('Proof_Seeker', 'Status_Conscious')
          AND estimated_value > 300000
        ORDER BY estimated_value DESC;
    """))
    
    # ZIP-level campaign planning
    conn.execute(text("""
        CREATE OR REPLACE VIEW zip_campaign_summary AS
        SELECT 
            zip_code,
            city,
            COUNT(*) as property_count,
            COUNT(DISTINCT persona) as persona_diversity,
            ROUND(AVG(sii_with_boost)::numeric) as avg_priority_score,
            ROUND(AVG(estimated_value)::numeric) as avg_value,
            ROUND(AVG(risk_score)::numeric, 1) as avg_risk,
            MODE() WITHIN GROUP (ORDER BY persona) as dominant_persona,
            MODE() WITHIN GROUP (ORDER BY recommended_play) as suggested_play,
            STRING_AGG(DISTINCT recommended_play, ', ') as play_mix
        FROM targeting_recommendations
        GROUP BY zip_code, city
        HAVING COUNT(*) >= 2
        ORDER BY avg_priority_score DESC;
    """))
    
    # Urgent follow-ups (tight SLA)
    conn.execute(text("""
        CREATE OR REPLACE VIEW urgent_follow_ups AS
        SELECT 
            property_id,
            address,
            city,
            persona,
            risk_category,
            recommended_play,
            follow_up_sla_hours,
            sii_with_boost as priority_score
        FROM targeting_recommendations
        WHERE follow_up_sla_hours <= 24
        ORDER BY follow_up_sla_hours ASC, sii_with_boost DESC;
    """))
    
    conn.commit()
    print("✅ Created 5 operator views:")
    print("   • high_priority_targets")
    print("   • financing_campaign_targets")
    print("   • premium_upsell_targets")
    print("   • zip_campaign_summary")
    print("   • urgent_follow_ups")
    
    conn.close()

def generate_campaign_specs():
    """Generate specific campaign configurations"""
    print("\n📢 Campaign Specifications")
    print("=" * 60)
    
    # High-priority financing campaign
    query = """
    SELECT 
        zip_code,
        COUNT(*) as target_count,
        ROUND(AVG(price_sensitivity)) as avg_price_sensitivity,
        ROUND(AVG(estimated_value)) as avg_value
    FROM targeting_recommendations
    WHERE persona = 'Deal_Hunter' AND risk_category IN ('High', 'Very High')
    GROUP BY zip_code
    HAVING COUNT(*) >= 3
    ORDER BY target_count DESC
    LIMIT 5
    """
    
    df = pd.read_sql(query, engine)
    print("\n💰 Top ZIPs for Financing Campaign (Deal_Hunter + High Risk):")
    print(df.to_string(index=False))
    
    # Premium material campaign
    query = """
    SELECT 
        zip_code,
        COUNT(*) as target_count,
        ROUND(AVG(estimated_value)) as avg_value,
        ROUND(AVG(risk_tolerance)) as avg_risk_tolerance
    FROM targeting_recommendations
    WHERE persona IN ('Proof_Seeker', 'Status_Conscious')
      AND estimated_value > 300000
    GROUP BY zip_code
    HAVING COUNT(*) >= 2
    ORDER BY avg_value DESC
    LIMIT 5
    """
    
    df = pd.read_sql(query, engine)
    print("\n✨ Top ZIPs for Premium Material Campaign:")
    print(df.to_string(index=False))

def main():
    print("🚀 Targeting Engine - Exploit Enriched Graph")
    print("=" * 60)
    
    try:
        # Generate recommendations
        rec_df = generate_targeting_recommendations()
        
        # Create operator views
        create_operator_views()
        
        # Generate campaign specs
        generate_campaign_specs()
        
        print("\n" + "=" * 60)
        print("✅ Targeting Engine Complete!")
        print("\n💡 Next steps:")
        print("   1. Query high_priority_targets for immediate outreach")
        print("   2. Use zip_campaign_summary for territory planning")
        print("   3. Filter urgent_follow_ups for tight SLA properties")
        print("   4. Feed sii_with_boost into SII models as features")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
