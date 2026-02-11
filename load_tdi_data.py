#!/usr/bin/env python3
"""
TDI Insurance Data Loader
Texas Department of Insurance P&C Market Data

Source: https://www.tdi.texas.gov/reports/report4.html
Downloads and processes ZIP-level insurance market data
"""

from sqlalchemy import create_engine, text
import pandas as pd
import requests
from io import StringIO

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

def download_tdi_data(year=2023):
    """
    Download TDI P&C Exhibit data
    
    Manual steps (until API available):
    1. Visit https://www.tdi.texas.gov/reports/report4.html
    2. Download "Property & Casualty Exhibit of Premiums and Losses"
    3. Filter for:
       - Line: Homeowners, Fire, Allied Lines
       - Geography: ZIP code level
       - Year: Most recent
    4. Save as CSV
    
    Returns path to downloaded file
    """
    print(f"\n📥 TDI Data Download Instructions")
    print("=" * 60)
    print(f"1. Visit: https://www.tdi.texas.gov/reports/report4.html")
    print(f"2. Download: P&C Exhibit of Premiums and Losses ({year})")
    print(f"3. Filter: Homeowners + Fire + Allied Lines, ZIP level")
    print(f"4. Save to: /tmp/tdi_pc_data_{year}.csv")
    print(f"\nOnce downloaded, run: load_tdi_data('/tmp/tdi_pc_data_{year}.csv')")
    
    return f"/tmp/tdi_pc_data_{year}.csv"

def load_tdi_data(csv_path):
    """
    Load TDI data from CSV into database
    
    Expected columns:
    - zip_code
    - direct_premiums_written
    - direct_losses_incurred
    - number_of_policies
    - carrier_count
    """
    print(f"\n📊 Loading TDI Data from {csv_path}")
    print("=" * 60)
    
    try:
        # Read CSV (adjust column names based on actual TDI format)
        df = pd.read_csv(csv_path)
        
        # Transform to our schema
        tdi_data = pd.DataFrame({
            'zip_code': df['ZIP_CODE'].astype(str).str.zfill(5),
            'hail_loss_ratio': (df['LOSSES_INCURRED'] / df['PREMIUMS_WRITTEN']).round(2),
            'property_loss_frequency': (df['CLAIM_COUNT'] / df['POLICY_COUNT'] * 1000).round(2),
            'avg_premium': (df['PREMIUMS_WRITTEN'] / df['POLICY_COUNT']).astype(int),
            'total_exposure': df['PREMIUMS_WRITTEN'].astype(int),
            'carrier_concentration': calculate_hhi(df),  # Herfindahl index
            'market_competitiveness': df['CARRIER_COUNT'].astype(int),
            'data_year': 2023
        })
        
        # Load to database
        conn = engine.connect()
        
        for _, row in tdi_data.iterrows():
            conn.execute(text("""
                INSERT INTO tdi_zip_insurance 
                (zip_code, hail_loss_ratio, property_loss_frequency, avg_premium,
                 total_exposure, carrier_concentration, market_competitiveness, data_year)
                VALUES (:zip, :loss_ratio, :freq, :premium, :exposure, :hhi, :comp, :year)
                ON CONFLICT (zip_code) DO UPDATE SET
                    hail_loss_ratio = EXCLUDED.hail_loss_ratio,
                    property_loss_frequency = EXCLUDED.property_loss_frequency,
                    avg_premium = EXCLUDED.avg_premium,
                    total_exposure = EXCLUDED.total_exposure,
                    carrier_concentration = EXCLUDED.carrier_concentration,
                    market_competitiveness = EXCLUDED.market_competitiveness,
                    data_year = EXCLUDED.data_year;
            """), {
                'zip': row['zip_code'],
                'loss_ratio': row['hail_loss_ratio'],
                'freq': row['property_loss_frequency'],
                'premium': row['avg_premium'],
                'exposure': row['total_exposure'],
                'hhi': row['carrier_concentration'],
                'comp': row['market_competitiveness'],
                'year': row['data_year']
            })
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ Loaded {len(tdi_data)} ZIP codes")
        print(f"  📊 Avg loss ratio: {tdi_data['hail_loss_ratio'].mean():.2f}")
        print(f"  💰 Avg premium: ${tdi_data['avg_premium'].mean():,.0f}")
        
        return tdi_data
        
    except FileNotFoundError:
        print(f"  ❌ File not found: {csv_path}")
        print(f"  💡 Run download_tdi_data() first")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def calculate_hhi(df):
    """Calculate Herfindahl-Hirschman Index for carrier concentration"""
    # Simplified - would need carrier-level data
    # For now, estimate from carrier count
    return 1.0 / df['CARRIER_COUNT']

def generate_synthetic_tdi_data():
    """
    Generate synthetic TDI data for testing
    Uses Dallas County ZIP codes
    """
    print("\n🔬 Generating Synthetic TDI Data (for testing)")
    print("=" * 60)
    
    # Get Dallas ZIPs from properties
    conn = engine.connect()
    result = conn.execute(text("SELECT DISTINCT zip_code FROM properties WHERE zip_code IS NOT NULL"))
    zip_codes = [row[0] for row in result.fetchall()]
    conn.close()
    
    import random
    
    synthetic_data = []
    for zip_code in zip_codes:
        synthetic_data.append({
            'zip_code': zip_code,
            'hail_loss_ratio': round(random.uniform(0.4, 1.2), 2),
            'property_loss_frequency': round(random.uniform(10, 80), 2),
            'avg_premium': random.randint(1200, 3500),
            'total_exposure': random.randint(5000000, 50000000),
            'carrier_concentration': round(random.uniform(0.15, 0.45), 2),
            'market_competitiveness': random.randint(3, 12),
            'data_year': 2023
        })
    
    df = pd.DataFrame(synthetic_data)
    
    # Load to database
    conn = engine.connect()
    for _, row in df.iterrows():
        conn.execute(text("""
            INSERT INTO tdi_zip_insurance 
            (zip_code, hail_loss_ratio, property_loss_frequency, avg_premium,
             total_exposure, carrier_concentration, market_competitiveness, data_year)
            VALUES (:zip, :loss_ratio, :freq, :premium, :exposure, :hhi, :comp, :year)
            ON CONFLICT (zip_code) DO UPDATE SET
                hail_loss_ratio = EXCLUDED.hail_loss_ratio,
                property_loss_frequency = EXCLUDED.property_loss_frequency,
                avg_premium = EXCLUDED.avg_premium,
                total_exposure = EXCLUDED.total_exposure,
                carrier_concentration = EXCLUDED.carrier_concentration,
                market_competitiveness = EXCLUDED.market_competitiveness,
                data_year = EXCLUDED.data_year;
        """), {
            'zip': row['zip_code'],
            'loss_ratio': float(row['hail_loss_ratio']),
            'freq': float(row['property_loss_frequency']),
            'premium': int(row['avg_premium']),
            'exposure': int(row['total_exposure']),
            'hhi': float(row['carrier_concentration']),
            'comp': int(row['market_competitiveness']),
            'year': int(row['data_year'])
        })
    
    conn.commit()
    conn.close()
    
    print(f"  ✅ Generated {len(df)} synthetic ZIP records")
    print(f"  📊 Loss ratio range: {df['hail_loss_ratio'].min():.2f} - {df['hail_loss_ratio'].max():.2f}")
    print(f"  💰 Premium range: ${df['avg_premium'].min():,} - ${df['avg_premium'].max():,}")
    
    return df

def main():
    print("🏢 TDI Insurance Data Loader")
    print("=" * 60)
    
    # For now, generate synthetic data
    print("\n⚠️  Using synthetic data for demonstration")
    print("   Replace with actual TDI data when available")
    
    df = generate_synthetic_tdi_data()
    
    # Verify load
    conn = engine.connect()
    result = conn.execute(text("SELECT COUNT(*) FROM tdi_zip_insurance"))
    count = result.fetchone()[0]
    print(f"\n✅ Total TDI records in database: {count}")
    
    # Sample query
    result = conn.execute(text("""
        SELECT zip_code, hail_loss_ratio, avg_premium, market_competitiveness
        FROM tdi_zip_insurance
        ORDER BY hail_loss_ratio DESC
        LIMIT 5
    """))
    
    print(f"\n📊 Top 5 ZIPs by Loss Ratio:")
    for row in result:
        print(f"   {row[0]}: Loss ratio {row[1]}, Premium ${row[2]:,}, {row[3]} carriers")
    
    conn.close()
    
    print("\n💡 Next: Run feature engineering to calculate insurance_burden_ratio")

if __name__ == "__main__":
    main()
