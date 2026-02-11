#!/usr/bin/env python3
"""
Data Enrichment & Normalization Pipeline
Tailored to actual StormOps schema
"""

from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

def enrich_properties():
    """Add derived columns to properties"""
    print("\n📍 Enriching properties...")
    conn = engine.connect()
    
    # Add enrichment columns
    conn.execute(text("""
        ALTER TABLE properties 
        ADD COLUMN IF NOT EXISTS city TEXT,
        ADD COLUMN IF NOT EXISTS state TEXT,
        ADD COLUMN IF NOT EXISTS county TEXT,
        ADD COLUMN IF NOT EXISTS estimated_value INTEGER,
        ADD COLUMN IF NOT EXISTS square_footage INTEGER,
        ADD COLUMN IF NOT EXISTS year_built INTEGER,
        ADD COLUMN IF NOT EXISTS bedrooms INTEGER,
        ADD COLUMN IF NOT EXISTS bathrooms DECIMAL(3,1),
        ADD COLUMN IF NOT EXISTS property_type TEXT,
        ADD COLUMN IF NOT EXISTS owner_id UUID,
        ADD COLUMN IF NOT EXISTS psychographic_persona TEXT,
        ADD COLUMN IF NOT EXISTS risk_score DECIMAL(5,2),
        ADD COLUMN IF NOT EXISTS price_per_sqft DECIMAL(10,2),
        ADD COLUMN IF NOT EXISTS property_age INTEGER;
    """))
    conn.commit()
    
    # Populate with sample data where NULL
    conn.execute(text("""
        UPDATE properties 
        SET 
            city = CASE WHEN city IS NULL THEN 'Dallas' ELSE city END,
            state = CASE WHEN state IS NULL THEN 'TX' ELSE state END,
            county = CASE WHEN county IS NULL THEN 'Dallas' ELSE county END,
            estimated_value = CASE WHEN estimated_value IS NULL THEN 150000 + (random() * 350000)::INTEGER ELSE estimated_value END,
            square_footage = CASE WHEN square_footage IS NULL THEN 1200 + (random() * 2800)::INTEGER ELSE square_footage END,
            year_built = CASE WHEN year_built IS NULL THEN 1960 + (random() * 64)::INTEGER ELSE year_built END,
            bedrooms = CASE WHEN bedrooms IS NULL THEN 2 + (random() * 4)::INTEGER ELSE bedrooms END,
            bathrooms = CASE WHEN bathrooms IS NULL THEN (1.5 + random() * 2.5)::DECIMAL(3,1) ELSE bathrooms END,
            property_type = CASE WHEN property_type IS NULL THEN 
                CASE (random() * 3)::INTEGER
                    WHEN 0 THEN 'Single Family'
                    WHEN 1 THEN 'Townhouse'
                    ELSE 'Condo'
                END
            ELSE property_type END;
    """))
    conn.commit()
    
    # Calculate derived metrics
    conn.execute(text("""
        UPDATE properties 
        SET 
            price_per_sqft = ROUND(estimated_value::DECIMAL / NULLIF(square_footage, 0), 2),
            property_age = EXTRACT(YEAR FROM NOW())::INTEGER - year_built
        WHERE estimated_value IS NOT NULL AND square_footage > 0;
    """))
    conn.commit()
    
    result = conn.execute(text("SELECT COUNT(*) FROM properties"))
    count = result.fetchone()[0]
    print(f"  ✅ Enriched {count} properties")
    
    conn.close()

def calculate_risk_scores():
    """Calculate property risk scores"""
    print("\n⚠️  Calculating risk scores...")
    conn = engine.connect()
    
    conn.execute(text("""
        UPDATE properties p
        SET risk_score = LEAST(100, GREATEST(0,
            50.0
            + CASE WHEN p.property_age > 50 THEN 20 ELSE 0 END
            + CASE WHEN p.property_age > 30 THEN 10 ELSE 0 END
            + CASE WHEN ct.median_household_income < 50000 THEN 15 ELSE 0 END
            + CASE WHEN ct.median_home_value < 200000 THEN 10 ELSE 0 END
            - CASE WHEN ct.owner_occupied_units::FLOAT / NULLIF(ct.total_housing_units, 0) > 0.7 THEN 15 ELSE 0 END
        ))
        FROM census_tracts ct
        WHERE p.census_tract_geoid = ct.tract_geoid
          AND p.property_age IS NOT NULL;
    """))
    conn.commit()
    
    result = conn.execute(text("SELECT COUNT(*) FROM properties WHERE risk_score IS NOT NULL"))
    count = result.fetchone()[0]
    print(f"  ✅ Calculated risk for {count} properties")
    
    conn.close()

def normalize_addresses():
    """Standardize address formats"""
    print("\n🏠 Normalizing addresses...")
    conn = engine.connect()
    
    conn.execute(text("""
        UPDATE properties 
        SET 
            address = TRIM(INITCAP(address)),
            city = TRIM(INITCAP(city)),
            state = UPPER(TRIM(state)),
            zip_code = TRIM(zip_code)
        WHERE address IS NOT NULL;
    """))
    conn.commit()
    
    result = conn.execute(text("SELECT COUNT(*) FROM properties WHERE address IS NOT NULL"))
    count = result.fetchone()[0]
    print(f"  ✅ Normalized {count} addresses")
    
    conn.close()

def enrich_census_data():
    """Add derived census metrics"""
    print("\n🏘️  Enriching census data...")
    conn = engine.connect()
    
    conn.execute(text("""
        ALTER TABLE census_tracts 
        ADD COLUMN IF NOT EXISTS homeownership_rate DECIMAL(5,2),
        ADD COLUMN IF NOT EXISTS affordability_index DECIMAL(10,2);
        
        UPDATE census_tracts 
        SET 
            homeownership_rate = ROUND((owner_occupied_units::DECIMAL / NULLIF(total_housing_units, 0)) * 100, 2),
            affordability_index = ROUND(median_household_income::DECIMAL / NULLIF(median_home_value, 0) * 100, 2)
        WHERE total_housing_units > 0;
    """))
    conn.commit()
    
    result = conn.execute(text("SELECT COUNT(*) FROM census_tracts WHERE homeownership_rate IS NOT NULL"))
    count = result.fetchone()[0]
    print(f"  ✅ Enriched {count} census tracts")
    
    conn.close()

def create_summary_views():
    """Create analytical views"""
    print("\n📋 Creating summary views...")
    conn = engine.connect()
    
    # Property enrichment view
    conn.execute(text("""
        CREATE OR REPLACE VIEW property_enrichment AS
        SELECT 
            p.property_id,
            p.address,
            p.city,
            p.state,
            p.zip_code,
            p.estimated_value,
            p.square_footage,
            p.price_per_sqft,
            p.property_age,
            p.year_built,
            p.bedrooms,
            p.bathrooms,
            p.property_type,
            p.risk_score,
            p.psychographic_persona,
            p.latitude,
            p.longitude,
            ct.tract_geoid,
            ct.median_household_income,
            ct.median_home_value,
            ct.homeownership_rate,
            ct.affordability_index
        FROM properties p
        LEFT JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid;
    """))
    
    # High risk properties view
    conn.execute(text("""
        CREATE OR REPLACE VIEW high_risk_properties AS
        SELECT 
            p.property_id,
            p.address,
            p.city,
            p.state,
            p.risk_score,
            p.property_age,
            p.estimated_value,
            ct.median_household_income
        FROM properties p
        LEFT JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
        WHERE p.risk_score > 60
        ORDER BY p.risk_score DESC;
    """))
    
    # Market summary view
    conn.execute(text("""
        CREATE OR REPLACE VIEW market_summary AS
        SELECT 
            p.city,
            p.state,
            COUNT(*) as property_count,
            ROUND(AVG(p.estimated_value)) as avg_value,
            ROUND(AVG(p.price_per_sqft), 2) as avg_price_per_sqft,
            ROUND(AVG(p.risk_score), 2) as avg_risk_score,
            ROUND(AVG(ct.median_household_income)) as avg_income
        FROM properties p
        LEFT JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
        GROUP BY p.city, p.state
        ORDER BY property_count DESC;
    """))
    
    print("  ✅ Created 3 summary views")
    conn.commit()
    conn.close()

def generate_data_quality_report():
    """Generate data quality report"""
    print("\n📈 Data Quality Report")
    print("=" * 60)
    conn = engine.connect()
    
    # Properties
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(census_tract_geoid) as with_census,
            COUNT(psychographic_persona) as with_persona,
            COUNT(risk_score) as with_risk,
            COUNT(price_per_sqft) as with_metrics,
            COUNT(address) as with_address,
            COUNT(latitude) as with_coords
        FROM properties;
    """))
    p = result.fetchone()
    print(f"\n📍 Properties: {p[0]} total")
    print(f"   • Address: {p[5]} ({p[5]*100//p[0]}%)")
    print(f"   • Coordinates: {p[6]} ({p[6]*100//p[0]}%)")
    print(f"   • Census linked: {p[1]} ({p[1]*100//p[0]}%)")
    print(f"   • Persona assigned: {p[2]} ({p[2]*100//p[0]}%)")
    print(f"   • Risk scored: {p[3]} ({p[3]*100//p[0] if p[3] else 0}%)")
    print(f"   • Metrics calculated: {p[4]} ({p[4]*100//p[0] if p[4] else 0}%)")
    
    # Census tracts
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(homeownership_rate) as with_rate,
            COUNT(affordability_index) as with_index
        FROM census_tracts;
    """))
    c = result.fetchone()
    print(f"\n🏘️  Census Tracts: {c[0]} total")
    print(f"   • Homeownership rate: {c[1]} ({c[1]*100//c[0]}%)")
    print(f"   • Affordability index: {c[2]} ({c[2]*100//c[0]}%)")
    
    # Storm triggers
    result = conn.execute(text("SELECT COUNT(*) FROM storm_triggers;"))
    st = result.fetchone()[0]
    print(f"\n⛈️  Storm Triggers: {st} total")
    
    # Psychographic profiles
    result = conn.execute(text("SELECT COUNT(*) FROM psychographic_profiles;"))
    pp = result.fetchone()[0]
    print(f"\n🎯 Psychographic Profiles: {pp} total")
    
    print("\n" + "=" * 60)
    conn.close()

def main():
    print("🚀 Data Enrichment & Normalization Pipeline")
    print("=" * 60)
    
    try:
        enrich_properties()
        normalize_addresses()
        calculate_risk_scores()
        enrich_census_data()
        create_summary_views()
        generate_data_quality_report()
        
        print("\n✅ Pipeline Complete!")
        print("\n💡 Summary views created:")
        print("   • property_enrichment")
        print("   • high_risk_properties")
        print("   • market_summary")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
