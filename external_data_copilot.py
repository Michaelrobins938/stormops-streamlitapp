#!/usr/bin/env python3
"""
External Data Copilot - Activates .env keys for production use
Integrates: Census (SES) + Google (geocoding) + NOAA (weather) + FireCrawl (intel)
"""

import os
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import json

# Load environment
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY', '0ffd1b5e9d4f1dd1157850f14cda45b0896463f0')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyCaTlC041dUyouJwoxBvKHSGuprPuhLtpY')
NOAA_TOKEN = os.getenv('NOAA_TOKEN', 'FQlQIOBWMisAdxyhMxgmNYSkqdOnWgig')
FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY', 'fc-73e16668b8b248ffa39a567ced30f012')

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

print("🚀 External Data Copilot - Activating APIs")
print("=" * 60)

# ============================================================================
# SERVICE 1: Google Geocoding + Address Enrichment
# ============================================================================

def geocode_and_enrich_properties():
    """Geocode properties and enrich with Google Places data."""
    print("\n📍 SERVICE 1: Google Geocoding & Enrichment")
    
    # Get properties without lat/lon
    query = """
    SELECT property_id, address, zip_code
    FROM properties
    WHERE latitude IS NULL OR longitude IS NULL
    LIMIT 100
    """
    
    df = pd.read_sql(query, engine)
    
    if len(df) == 0:
        print("  ✅ All properties already geocoded")
        return
    
    enriched = []
    for _, row in df.iterrows():
        try:
            # Geocode with Google
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': f"{row['address']}, {row['zip_code']}, TX",
                'key': GOOGLE_API_KEY
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data['status'] == 'OK':
                result = data['results'][0]
                location = result['geometry']['location']
                
                enriched.append({
                    'property_id': row['property_id'],
                    'latitude': location['lat'],
                    'longitude': location['lng'],
                    'formatted_address': result['formatted_address'],
                    'place_id': result.get('place_id')
                })
        except Exception as e:
            print(f"  ⚠️  Error geocoding {row['address']}: {e}")
    
    # Update database
    if enriched:
        for prop in enriched:
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE properties
                    SET latitude = :lat, longitude = :lon
                    WHERE property_id = :id
                """), {'lat': prop['latitude'], 'lon': prop['longitude'], 'id': prop['property_id']})
                conn.commit()
        
        print(f"  ✅ Geocoded {len(enriched)} properties")
    
    return enriched


# ============================================================================
# SERVICE 2: Census SES Enrichment
# ============================================================================

def enrich_properties_with_census():
    """Enrich properties with Census tract-level SES data."""
    print("\n🏘️  SERVICE 2: Census SES Enrichment")
    
    # Get properties with census tract but no enrichment
    query = """
    SELECT DISTINCT p.census_tract_geoid
    FROM properties p
    LEFT JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
    WHERE p.census_tract_geoid IS NOT NULL
      AND ct.tract_geoid IS NULL
    LIMIT 50
    """
    
    df = pd.read_sql(query, engine)
    
    if len(df) == 0:
        print("  ✅ All tracts already enriched")
        return
    
    # Fetch from Census API
    variables = [
        'B19013_001E',  # Median household income
        'B25077_001E',  # Median home value
        'B25001_001E',  # Total housing units
        'B25003_002E',  # Owner-occupied
        'B15003_022E',  # Bachelor's degree+
        'B25034_001E'   # Median year built
    ]
    
    enriched_tracts = []
    for geoid in df['census_tract_geoid']:
        try:
            url = f"https://api.census.gov/data/2023/acs/acs5"
            params = {
                'get': f"NAME,{','.join(variables)}",
                'for': f"tract:{geoid[-6:]}",
                'in': f"state:{geoid[:2]}+county:{geoid[2:5]}",
                'key': CENSUS_API_KEY
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if len(data) > 1:
                row = data[1]
                enriched_tracts.append({
                    'tract_geoid': geoid,
                    'median_household_income': int(row[1]) if row[1] else None,
                    'median_home_value': int(row[2]) if row[2] else None,
                    'total_housing_units': int(row[3]) if row[3] else None,
                    'owner_occupied_units': int(row[4]) if row[4] else None,
                    'bachelors_or_higher_pct': float(row[5]) / float(row[3]) * 100 if row[5] and row[3] else None,
                    'median_year_built': int(row[6]) if row[6] else None
                })
        except Exception as e:
            print(f"  ⚠️  Error fetching tract {geoid}: {e}")
    
    # Insert into database
    if enriched_tracts:
        pd.DataFrame(enriched_tracts).to_sql('census_tracts', engine, if_exists='append', index=False)
        print(f"  ✅ Enriched {len(enriched_tracts)} census tracts")
    
    return enriched_tracts


# ============================================================================
# SERVICE 3: NOAA Weather Triggers
# ============================================================================

def check_noaa_recent_events():
    """Check NOAA for recent storm events and trigger StormOps state changes."""
    print("\n⛈️  SERVICE 3: NOAA Weather Triggers")
    
    # Check for events in last 7 days
    query = """
    SELECT event_id, event_type, begin_datetime, county, magnitude
    FROM storm_events
    WHERE begin_datetime > NOW() - INTERVAL '7 days'
      AND event_type IN ('Hail', 'Thunderstorm Wind')
      AND state = 'TEXAS'
    ORDER BY begin_datetime DESC
    LIMIT 10
    """
    
    df = pd.read_sql(query, engine)
    
    if len(df) == 0:
        print("  ℹ️  No recent storm events")
        return []
    
    print(f"  ✅ Found {len(df)} recent storm events")
    
    # Trigger state transitions for each event
    triggers = []
    for _, event in df.iterrows():
        # Check if we've already processed this event
        check = pd.read_sql(
            "SELECT 1 FROM storm_triggers WHERE event_id = :eid",
            engine,
            params={'eid': event['event_id']}
        )
        
        if len(check) == 0:
            # New event - trigger StormOps
            trigger = {
                'event_id': event['event_id'],
                'event_type': event['event_type'],
                'magnitude': event['magnitude'],
                'county': event['county'],
                'triggered_at': datetime.now(),
                'state_transition': 'S0_to_S1',  # Monitoring → Target Acquisition
                'action': 'generate_leads'
            }
            triggers.append(trigger)
            
            # Log trigger
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO storm_triggers (event_id, triggered_at, action)
                    VALUES (:eid, :ts, :action)
                    ON CONFLICT DO NOTHING
                """), {'eid': event['event_id'], 'ts': datetime.now(), 'action': 'generate_leads'})
                conn.commit()
            
            print(f"  🚨 TRIGGER: {event['event_type']} in {event['county']} ({event['magnitude']})")
    
    return triggers


# ============================================================================
# SERVICE 4: FireCrawl Competitor Intelligence
# ============================================================================

def crawl_competitor_sites():
    """Use FireCrawl to harvest competitor intelligence."""
    print("\n🕷️  SERVICE 4: FireCrawl Competitor Intelligence")
    
    # Competitor sites to monitor
    competitors = [
        {'name': 'ABC Roofing', 'url': 'https://example-roofing-1.com'},
        {'name': 'XYZ Contractors', 'url': 'https://example-roofing-2.com'}
    ]
    
    intel = []
    for comp in competitors:
        try:
            # FireCrawl API
            url = "https://api.firecrawl.dev/v0/scrape"
            headers = {
                'Authorization': f'Bearer {FIRECRAWL_API_KEY}',
                'Content-Type': 'application/json'
            }
            payload = {
                'url': comp['url'],
                'formats': ['markdown', 'html']
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                intel.append({
                    'competitor_name': comp['name'],
                    'url': comp['url'],
                    'content': data.get('markdown', '')[:5000],  # First 5K chars
                    'crawled_at': datetime.now()
                })
                
                print(f"  ✅ Crawled: {comp['name']}")
            else:
                print(f"  ⚠️  Failed: {comp['name']} - {response.status_code}")
                
        except Exception as e:
            print(f"  ⚠️  Error crawling {comp['name']}: {e}")
    
    # Store in database
    if intel:
        pd.DataFrame(intel).to_sql('competitor_intel', engine, if_exists='append', index=False)
    
    return intel


# ============================================================================
# SERVICE 5: Psychographic Segmentation
# ============================================================================

def calculate_psychographic_segments():
    """Calculate psychographic segments from Census + behavioral data."""
    print("\n🎯 SERVICE 5: Psychographic Segmentation")
    
    query = """
    SELECT 
        p.property_id,
        ct.median_household_income,
        ct.median_home_value,
        ct.owner_occupied_units::float / NULLIF(ct.total_housing_units, 0) as homeownership_rate
    FROM properties p
    JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
    WHERE ct.median_household_income IS NOT NULL
    LIMIT 1000
    """
    
    df = pd.read_sql(query, engine)
    
    if len(df) == 0:
        print("  ℹ️  No properties with census data")
        return
    
    # Simple segmentation logic
    def assign_persona(row):
        income = row['median_household_income']
        home_value = row['median_home_value']
        
        if income > 100000:
            return 'Proof_Seeker'
        elif income > 80000 and home_value > 300000:
            return 'Status_Conscious'
        elif income < 60000:
            return 'Deal_Hunter'
        else:
            return 'Family_Protector'
    
    df['persona'] = df.apply(assign_persona, axis=1)
    
    # Calculate scores
    df['risk_tolerance'] = (df['median_household_income'] / 150000 * 100).clip(0, 100)
    df['price_sensitivity'] = (100 - df['median_household_income'] / 150000 * 100).clip(0, 100)
    
    # Update database
    profiles = df[['property_id', 'persona', 'risk_tolerance', 'price_sensitivity']].to_dict('records')
    
    for profile in profiles:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO psychographic_profiles (property_id, primary_persona, risk_tolerance, price_sensitivity)
                VALUES (:pid, :persona, :risk, :price)
                ON CONFLICT (property_id) DO UPDATE
                SET primary_persona = EXCLUDED.primary_persona,
                    risk_tolerance = EXCLUDED.risk_tolerance,
                    price_sensitivity = EXCLUDED.price_sensitivity
            """), {
                'pid': profile['property_id'],
                'persona': profile['persona'],
                'risk': profile['risk_tolerance'],
                'price': profile['price_sensitivity']
            })
            conn.commit()
    
    print(f"  ✅ Segmented {len(profiles)} properties")
    print(f"     Personas: {df['persona'].value_counts().to_dict()}")
    
    return profiles


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create required tables
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS storm_triggers (
                event_id TEXT PRIMARY KEY,
                triggered_at TIMESTAMP,
                action TEXT
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS competitor_intel (
                id SERIAL PRIMARY KEY,
                competitor_name TEXT,
                url TEXT,
                content TEXT,
                crawled_at TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS psychographic_profiles (
                property_id UUID PRIMARY KEY,
                primary_persona TEXT,
                risk_tolerance DECIMAL(5,2),
                price_sensitivity DECIMAL(5,2),
                calculated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.commit()
    
    # Run all services
    geocode_and_enrich_properties()
    enrich_properties_with_census()
    check_noaa_recent_events()
    # crawl_competitor_sites()  # Uncomment when ready
    calculate_psychographic_segments()
    
    print("\n" + "=" * 60)
    print("✅ External Data Copilot Complete!")
    print("\n📊 Summary:")
    print("  • Google: Geocoding & address enrichment")
    print("  • Census: SES & demographic enrichment")
    print("  • NOAA: Weather triggers & state transitions")
    print("  • Psychographics: Persona segmentation")
    print("\n💡 Run this script on a schedule (cron/Airflow) for continuous enrichment")
