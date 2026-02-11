#!/usr/bin/env python3
"""
Feature Engineering for SII/MOE Models
Robust feature creation with scaling and interaction terms
"""

from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

def create_interaction_features():
    """Create interaction features for better model discrimination"""
    print("\n🔧 Creating Interaction Features")
    print("=" * 60)
    
    conn = engine.connect()
    
    # Add interaction columns
    conn.execute(text("""
        ALTER TABLE properties 
        ADD COLUMN IF NOT EXISTS age_risk_interaction DECIMAL(10,2),
        ADD COLUMN IF NOT EXISTS value_ses_interaction DECIMAL(10,2),
        ADD COLUMN IF NOT EXISTS sqft_value_ratio DECIMAL(10,4);
    """))
    
    # Age × Risk interaction
    conn.execute(text("""
        UPDATE properties 
        SET age_risk_interaction = property_age * risk_score / 100.0
        WHERE property_age IS NOT NULL AND risk_score IS NOT NULL;
    """))
    print("  ✅ Created age_risk_interaction")
    
    # Value × SES interaction
    conn.execute(text("""
        UPDATE properties p
        SET value_ses_interaction = 
            (p.estimated_value / 100000.0) * (ct.median_household_income / 10000.0)
        FROM census_tracts ct
        WHERE p.census_tract_geoid = ct.tract_geoid
          AND p.estimated_value IS NOT NULL
          AND ct.median_household_income > 0;
    """))
    print("  ✅ Created value_ses_interaction")
    
    # Sqft/Value ratio (efficiency metric)
    conn.execute(text("""
        UPDATE properties 
        SET sqft_value_ratio = square_footage::DECIMAL / NULLIF(estimated_value, 0)
        WHERE square_footage IS NOT NULL AND estimated_value > 0;
    """))
    print("  ✅ Created sqft_value_ratio")
    
    conn.commit()
    conn.close()

def create_scaled_features():
    """Create standardized features for ML models"""
    print("\n📊 Creating Scaled Features")
    print("=" * 60)
    
    # Load data
    query = """
    SELECT 
        p.property_id,
        p.estimated_value,
        p.square_footage,
        p.property_age,
        p.risk_score,
        p.price_per_sqft,
        pp.risk_tolerance,
        pp.price_sensitivity,
        ct.median_household_income,
        ct.median_home_value,
        ct.homeownership_rate,
        ct.affordability_index
    FROM properties p
    LEFT JOIN psychographic_profiles pp ON p.property_id = pp.property_id
    LEFT JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
    WHERE p.estimated_value IS NOT NULL
    """
    
    df = pd.read_sql(query, engine)
    
    # Features to scale
    scale_features = [
        'estimated_value', 'square_footage', 'property_age', 
        'price_per_sqft', 'median_household_income', 'median_home_value'
    ]
    
    # Use RobustScaler (less sensitive to outliers)
    scaler = RobustScaler()
    
    for feature in scale_features:
        if feature in df.columns:
            valid_mask = df[feature].notna()
            if valid_mask.sum() > 0:
                df.loc[valid_mask, f'{feature}_scaled'] = scaler.fit_transform(
                    df.loc[valid_mask, [feature]]
                )
    
    # Save scaled features back to database
    conn = engine.connect()
    
    for feature in scale_features:
        scaled_col = f'{feature}_scaled'
        if scaled_col in df.columns:
            conn.execute(text(f"""
                ALTER TABLE properties 
                ADD COLUMN IF NOT EXISTS {scaled_col} DECIMAL(10,4);
            """))
            
            for _, row in df.iterrows():
                if pd.notna(row.get(scaled_col)):
                    conn.execute(text(f"""
                        UPDATE properties 
                        SET {scaled_col} = :val
                        WHERE property_id = :pid
                    """), {'val': float(row[scaled_col]), 'pid': row['property_id']})
    
    conn.commit()
    conn.close()
    
    print(f"  ✅ Scaled {len(scale_features)} features using RobustScaler")

def create_model_feature_view():
    """Create view with all model-ready features"""
    print("\n📋 Creating Model Feature View")
    print("=" * 60)
    
    conn = engine.connect()
    
    conn.execute(text("""
        CREATE OR REPLACE VIEW model_features AS
        SELECT 
            p.property_id,
            p.address,
            p.city,
            p.zip_code,
            
            -- Raw features
            p.estimated_value,
            p.square_footage,
            p.property_age,
            p.risk_score,
            p.price_per_sqft,
            
            -- Scaled features
            p.estimated_value_scaled,
            p.square_footage_scaled,
            p.property_age_scaled,
            p.price_per_sqft_scaled,
            
            -- Interaction features
            p.age_risk_interaction,
            p.value_ses_interaction,
            p.sqft_value_ratio,
            
            -- Psychographic features
            pp.primary_persona,
            pp.risk_tolerance,
            pp.price_sensitivity,
            
            -- Census/SES features
            ct.median_household_income,
            ct.median_home_value,
            ct.homeownership_rate,
            ct.affordability_index,
            
            -- Targeting features
            tr.recommended_play,
            tr.sii_with_boost as sii_score,
            tr.follow_up_sla_hours
            
        FROM properties p
        LEFT JOIN psychographic_profiles pp ON p.property_id = pp.property_id
        LEFT JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
        LEFT JOIN targeting_recommendations tr ON p.property_id::text = tr.property_id
        WHERE p.estimated_value IS NOT NULL;
    """))
    
    print("  ✅ Created model_features view")
    
    conn.commit()
    conn.close()

def generate_feature_summary():
    """Generate feature engineering summary"""
    print("\n📈 Feature Engineering Summary")
    print("=" * 60)
    
    conn = engine.connect()
    
    # Count features
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total_properties,
            COUNT(age_risk_interaction) as with_age_risk,
            COUNT(value_ses_interaction) as with_value_ses,
            COUNT(sqft_value_ratio) as with_sqft_ratio,
            COUNT(estimated_value_scaled) as with_scaled
        FROM properties;
    """))
    
    r = result.fetchone()
    print(f"\n✅ Feature Coverage:")
    print(f"   Total properties: {r[0]}")
    print(f"   Age×Risk interaction: {r[1]} ({r[1]*100//r[0]}%)")
    print(f"   Value×SES interaction: {r[2]} ({r[2]*100//r[0]}%)")
    print(f"   Sqft/Value ratio: {r[3]} ({r[3]*100//r[0]}%)")
    print(f"   Scaled features: {r[4]} ({r[4]*100//r[0]}%)")
    
    # Sample statistics
    result = conn.execute(text("""
        SELECT 
            ROUND(AVG(age_risk_interaction), 2) as avg_age_risk,
            ROUND(AVG(value_ses_interaction), 2) as avg_value_ses,
            ROUND(AVG(sqft_value_ratio), 4) as avg_sqft_ratio
        FROM properties
        WHERE age_risk_interaction IS NOT NULL;
    """))
    
    r = result.fetchone()
    print(f"\n📊 Feature Statistics:")
    print(f"   Avg age×risk: {r[0]}")
    print(f"   Avg value×SES: {r[1]}")
    print(f"   Avg sqft/value: {r[2]}")
    
    conn.close()

def export_model_dataset():
    """Export clean dataset for model training"""
    print("\n💾 Exporting Model Dataset")
    print("=" * 60)
    
    query = "SELECT * FROM model_features"
    df = pd.read_sql(query, engine)
    
    output_path = '/home/forsythe/kirocli/kirocli/model_features.csv'
    df.to_csv(output_path, index=False)
    
    print(f"  ✅ Exported {len(df)} rows to model_features.csv")
    print(f"  ✅ {len(df.columns)} features available")
    
    # Feature list for documentation
    print(f"\n📋 Available Features:")
    feature_groups = {
        'Raw': ['estimated_value', 'square_footage', 'property_age', 'risk_score', 'price_per_sqft'],
        'Scaled': ['estimated_value_scaled', 'square_footage_scaled', 'property_age_scaled'],
        'Interactions': ['age_risk_interaction', 'value_ses_interaction', 'sqft_value_ratio'],
        'Psychographic': ['primary_persona', 'risk_tolerance', 'price_sensitivity'],
        'SES': ['median_household_income', 'median_home_value', 'homeownership_rate', 'affordability_index'],
        'Targeting': ['recommended_play', 'sii_score', 'follow_up_sla_hours']
    }
    
    for group, features in feature_groups.items():
        available = [f for f in features if f in df.columns]
        print(f"   {group}: {len(available)} features")

def main():
    print("🚀 Feature Engineering Pipeline")
    print("=" * 60)
    
    try:
        create_interaction_features()
        create_scaled_features()
        create_model_feature_view()
        generate_feature_summary()
        export_model_dataset()
        
        print("\n" + "=" * 60)
        print("✅ Feature Engineering Complete!")
        print("\n💡 Next steps:")
        print("   1. Use model_features view for SII/MOE training")
        print("   2. Import model_features.csv into ML pipeline")
        print("   3. Test SHAP/feature importance on new features")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
