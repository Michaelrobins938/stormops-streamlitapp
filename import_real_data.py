#!/usr/bin/env python3
# Step 3: Import Real Data (NOAA, Permits, Census)

import requests
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import os
import sys

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

print("📊 Importing Real Data")
print("=" * 50)

# 1. NOAA Storm Events
print("\n⛈️  Importing NOAA Storm Events...")
try:
    # Download actual NOAA data for Texas 2023 (latest available)
    year = 2023
    url = f"https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_details-ftp_v1.0_d{year}_c20260116.csv.gz"
    
    print(f"  Downloading from NOAA: {url}")
    df = pd.read_csv(url, compression='gzip')
    
    # Filter for Texas hail events
    texas_hail = df[
        (df['STATE'] == 'TEXAS') & 
        (df['EVENT_TYPE'].isin(['Hail', 'Thunderstorm Wind']))
    ].copy()
    
    # Rename columns to match schema
    texas_hail['event_id'] = 'noaa_' + texas_hail['EVENT_ID'].astype(str)
    texas_hail['event_type'] = texas_hail['EVENT_TYPE']
    texas_hail['begin_datetime'] = pd.to_datetime(texas_hail['BEGIN_DATE_TIME'])
    texas_hail['state'] = texas_hail['STATE']
    texas_hail['county'] = texas_hail['CZ_NAME']
    texas_hail['magnitude'] = texas_hail['MAGNITUDE']
    texas_hail['damage_property'] = texas_hail['DAMAGE_PROPERTY'].replace('K', '000', regex=True).replace('M', '000000', regex=True).astype(float)
    texas_hail['begin_lat'] = texas_hail['BEGIN_LAT']
    texas_hail['begin_lon'] = texas_hail['BEGIN_LON']
    
    # Select relevant columns
    storm_events = texas_hail[[
        'event_id', 'event_type', 'begin_datetime', 'state', 'county',
        'magnitude', 'damage_property', 'begin_lat', 'begin_lon'
    ]]
    
    storm_events.to_sql('storm_events', engine, if_exists='append', index=False)
    print(f"  ✅ Imported {len(storm_events)} real NOAA storm events")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    print(f"  💡 Download manually from: https://www.ncei.noaa.gov/stormevents/")
    sys.exit(1)

# 2. Dallas Building Permits
print("\n🏗️  Importing Dallas Building Permits...")
try:
    # Dallas Open Data Socrata API
    url = "https://www.dallasopendata.com/resource/e7gq-4sah.json"
    
    # Query for all building permits (we'll filter for roofing later)
    params = {
        "$limit": 5000,
        "$order": "issued_date DESC"
    }
    
    print(f"  Fetching from Dallas Open Data API...")
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    
    permits_data = response.json()
    permits = pd.DataFrame(permits_data)
    
    # Rename columns to match schema
    permits['permit_id'] = permits.get('permit_number')
    permits['permit_type'] = permits.get('permit_type')
    permits['issue_date'] = pd.to_datetime(permits.get('issued_date'), errors='coerce')
    permits['address'] = permits.get('street_address')
    permits['zip_code'] = permits.get('zip_code')
    permits['contractor_name'] = permits.get('contractor', pd.Series([''] * len(permits))).astype(str).str.split(' ', n=3).str[:3].str.join(' ')  # Extract name only
    permits['valuation'] = pd.to_numeric(permits.get('value', 0), errors='coerce')
    
    # Select relevant columns
    permits_clean = permits[[
        'permit_id', 'permit_type', 'issue_date', 'address', 
        'zip_code', 'contractor_name', 'valuation'
    ]].dropna(subset=['permit_id'])
    
    permits_clean.to_sql('building_permits', engine, if_exists='append', index=False)
    print(f"  ✅ Imported {len(permits_clean)} real Dallas building permits")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    print(f"  💡 Check Dallas Open Data: https://www.dallasopendata.com/")
    sys.exit(1)

# 3. Census ACS Data
print("\n🏘️  Importing Census ACS Data...")
try:
    # Census API - requires key
    census_key = os.getenv('CENSUS_API_KEY')
    if not census_key:
        print(f"  ❌ CENSUS_API_KEY not set")
        print(f"  💡 Get key: https://api.census.gov/data/key_signup.html")
        print(f"  💡 Then: export CENSUS_API_KEY=your_key")
        sys.exit(1)
    
    # ACS 5-year data for Dallas County tracts
    year = 2023
    variables = [
        'B19013_001E',  # Median household income
        'B25077_001E',  # Median home value
        'B25001_001E',  # Total housing units
        'B25003_002E',  # Owner-occupied units
        'B25034_001E'   # Median year built
    ]
    
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {
        'get': f"NAME,{','.join(variables)}",
        'for': 'tract:*',
        'in': 'state:48+county:113',  # Texas, Dallas County
        'key': census_key
    }
    
    print(f"  Fetching from Census API...")
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    headers = data[0]
    rows = data[1:]
    
    census_df = pd.DataFrame(rows, columns=headers)
    
    # Build GEOID
    census_df['tract_geoid'] = (
        census_df['state'] + 
        census_df['county'] + 
        census_df['tract']
    )
    
    # Rename columns
    census_tracts = pd.DataFrame({
        'tract_geoid': census_df['tract_geoid'],
        'state_fips': census_df['state'],
        'county_fips': census_df['county'],
        'tract_name': census_df['NAME'],
        'median_household_income': pd.to_numeric(census_df['B19013_001E'], errors='coerce'),
        'median_home_value': pd.to_numeric(census_df['B25077_001E'], errors='coerce'),
        'total_housing_units': pd.to_numeric(census_df['B25001_001E'], errors='coerce'),
        'owner_occupied_units': pd.to_numeric(census_df['B25003_002E'], errors='coerce'),
        'median_year_built': pd.to_numeric(census_df['B25034_001E'], errors='coerce')
    })
    
    census_tracts.to_sql('census_tracts', engine, if_exists='append', index=False)
    print(f"  ✅ Imported {len(census_tracts)} real Census tracts (Dallas County)")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    print(f"  💡 Get Census API key: https://api.census.gov/data/key_signup.html")
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ Real Data Import Complete!")
print("\n📊 Summary:")
print(f"  NOAA Storm Events: {len(storm_events)} (Texas hail/wind)")
print(f"  Dallas Permits: {len(permits_clean)} (roofing)")
print(f"  Census Tracts: {len(census_tracts)} (Dallas County)")
print("\n💡 Next: python enable_ga4.py")
