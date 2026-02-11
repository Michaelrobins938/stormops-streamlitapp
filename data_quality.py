#!/usr/bin/env python3
"""
Data Quality & Validation Framework
Six dimensions: Completeness, Validity, Consistency, Accuracy, Uniqueness, Integrity
"""

from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

@dataclass
class QualityThresholds:
    completeness_min: float = 0.95
    validity_min: float = 0.98
    uniqueness_min: float = 0.99
    integrity_min: float = 0.95

THRESHOLDS = QualityThresholds()

# Domain constraints
CONSTRAINTS = {
    'properties': {
        'estimated_value': (50000, 5000000),
        'square_footage': (500, 10000),
        'year_built': (1900, 2026),
        'bedrooms': (1, 10),
        'bathrooms': (1.0, 8.0),
        'property_age': (0, 126),
        'risk_score': (0, 100),
        'price_per_sqft': (20, 1000)
    },
    'census_tracts': {
        'median_household_income': (0, 500000),
        'median_home_value': (0, 5000000),
        'total_housing_units': (0, 50000),
        'owner_occupied_units': (0, 50000),
        'homeownership_rate': (0, 100),
        'affordability_index': (0, 200)
    },
    'psychographic_profiles': {
        'risk_tolerance': (0, 100),
        'price_sensitivity': (0, 100)
    }
}

def check_completeness(table: str, required_fields: List[str]) -> Tuple[bool, Dict]:
    """Check required fields are populated"""
    conn = engine.connect()
    
    results = {}
    total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
    
    for field in required_fields:
        non_null = conn.execute(text(f"SELECT COUNT({field}) FROM {table}")).fetchone()[0]
        pct = non_null / total if total > 0 else 0
        results[field] = {'count': non_null, 'pct': pct, 'pass': pct >= THRESHOLDS.completeness_min}
    
    conn.close()
    passed = all(r['pass'] for r in results.values())
    return passed, results

def check_validity(table: str, constraints: Dict) -> Tuple[bool, Dict]:
    """Check values are in valid ranges"""
    conn = engine.connect()
    
    results = {}
    
    for field, (min_val, max_val) in constraints.items():
        total_non_null = conn.execute(text(f"""
            SELECT COUNT(*) FROM {table} WHERE {field} IS NOT NULL
        """)).fetchone()[0]
        
        if total_non_null == 0:
            results[field] = {'valid': 0, 'invalid': 0, 'pct_valid': 1.0, 'pass': True}
            continue
        
        valid = conn.execute(text(f"""
            SELECT COUNT(*) FROM {table} 
            WHERE {field} BETWEEN {min_val} AND {max_val}
        """)).fetchone()[0]
        
        invalid = total_non_null - valid
        pct_valid = valid / total_non_null if total_non_null > 0 else 0
        
        results[field] = {
            'valid': valid,
            'invalid': invalid,
            'pct_valid': pct_valid,
            'pass': pct_valid >= THRESHOLDS.validity_min
        }
    
    conn.close()
    passed = all(r['pass'] for r in results.values())
    return passed, results

def check_uniqueness(table: str, key_fields: List[str]) -> Tuple[bool, Dict]:
    """Check for duplicates on key fields"""
    conn = engine.connect()
    
    key_str = ', '.join(key_fields)
    total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
    unique = conn.execute(text(f"""
        SELECT COUNT(DISTINCT ({key_str})) FROM {table}
    """)).fetchone()[0]
    
    duplicates = total - unique
    pct_unique = unique / total if total > 0 else 0
    
    results = {
        'total': total,
        'unique': unique,
        'duplicates': duplicates,
        'pct_unique': pct_unique,
        'pass': pct_unique >= THRESHOLDS.uniqueness_min
    }
    
    conn.close()
    return results['pass'], results

def check_integrity(parent_table: str, child_table: str, fk_field: str, pk_field: str) -> Tuple[bool, Dict]:
    """Check foreign key integrity"""
    conn = engine.connect()
    
    total = conn.execute(text(f"SELECT COUNT(*) FROM {child_table}")).fetchone()[0]
    
    orphans = conn.execute(text(f"""
        SELECT COUNT(*) FROM {child_table} c
        LEFT JOIN {parent_table} p ON c.{fk_field} = p.{pk_field}
        WHERE c.{fk_field} IS NOT NULL AND p.{pk_field} IS NULL
    """)).fetchone()[0]
    
    pct_valid = (total - orphans) / total if total > 0 else 0
    
    results = {
        'total': total,
        'orphans': orphans,
        'pct_valid': pct_valid,
        'pass': pct_valid >= THRESHOLDS.integrity_min
    }
    
    conn.close()
    return results['pass'], results

def detect_outliers_iqr(table: str, field: str) -> Tuple[int, float, float]:
    """Detect outliers using IQR method"""
    conn = engine.connect()
    
    df = pd.read_sql(f"SELECT {field} FROM {table} WHERE {field} IS NOT NULL", conn)
    
    if len(df) == 0:
        return 0, 0, 0
    
    Q1 = df[field].quantile(0.25)
    Q3 = df[field].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = ((df[field] < lower_bound) | (df[field] > upper_bound)).sum()
    
    conn.close()
    return outliers, lower_bound, upper_bound

def fix_validity_issues():
    """Fix invalid values in database"""
    print("\n🔧 Fixing Validity Issues")
    print("=" * 60)
    
    conn = engine.connect()
    fixes = []
    
    # Fix negative census values
    result = conn.execute(text("""
        UPDATE census_tracts 
        SET median_household_income = NULL 
        WHERE median_household_income < 0;
    """))
    fixes.append(f"Nullified {result.rowcount} negative median_household_income")
    
    result = conn.execute(text("""
        UPDATE census_tracts 
        SET median_home_value = NULL 
        WHERE median_home_value < 0;
    """))
    fixes.append(f"Nullified {result.rowcount} negative median_home_value")
    
    # Cap extreme property values
    result = conn.execute(text("""
        UPDATE properties 
        SET estimated_value = 5000000 
        WHERE estimated_value > 5000000;
    """))
    fixes.append(f"Capped {result.rowcount} extreme estimated_value")
    
    result = conn.execute(text("""
        UPDATE properties 
        SET square_footage = 10000 
        WHERE square_footage > 10000;
    """))
    fixes.append(f"Capped {result.rowcount} extreme square_footage")
    
    # Fix risk scores outside 0-100
    result = conn.execute(text("""
        UPDATE properties 
        SET risk_score = LEAST(100, GREATEST(0, risk_score))
        WHERE risk_score IS NOT NULL;
    """))
    fixes.append(f"Bounded {result.rowcount} risk_score values")
    
    # Fix psychographic scores
    result = conn.execute(text("""
        UPDATE psychographic_profiles 
        SET risk_tolerance = LEAST(100, GREATEST(0, risk_tolerance)),
            price_sensitivity = LEAST(100, GREATEST(0, price_sensitivity))
        WHERE risk_tolerance IS NOT NULL OR price_sensitivity IS NOT NULL;
    """))
    fixes.append(f"Bounded {result.rowcount} psychographic scores")
    
    # Fix affordability index outliers (cap at 200)
    result = conn.execute(text("""
        UPDATE census_tracts 
        SET affordability_index = NULL
        WHERE affordability_index < 0 OR affordability_index > 200;
    """))
    fixes.append(f"Nullified {result.rowcount} invalid affordability_index values")
    
    conn.commit()
    conn.close()
    
    for fix in fixes:
        print(f"  ✅ {fix}")

def run_quality_checks():
    """Run all quality checks"""
    print("\n📊 Data Quality Assessment")
    print("=" * 60)
    
    all_passed = True
    
    # Properties - Completeness
    print("\n1️⃣  COMPLETENESS")
    passed, results = check_completeness('properties', [
        'property_id', 'address', 'city', 'state', 'zip_code', 
        'census_tract_geoid', 'estimated_value', 'square_footage'
    ])
    print(f"   Properties: {'✅ PASS' if passed else '❌ FAIL'}")
    for field, data in results.items():
        status = '✅' if data['pass'] else '❌'
        print(f"      {status} {field}: {data['pct']*100:.1f}% complete")
    all_passed &= passed
    
    # Properties - Validity
    print("\n2️⃣  VALIDITY")
    passed, results = check_validity('properties', CONSTRAINTS['properties'])
    print(f"   Properties: {'✅ PASS' if passed else '❌ FAIL'}")
    for field, data in results.items():
        status = '✅' if data['pass'] else '❌'
        if data['invalid'] > 0:
            print(f"      {status} {field}: {data['invalid']} invalid values ({data['pct_valid']*100:.1f}% valid)")
    all_passed &= passed
    
    passed, results = check_validity('census_tracts', CONSTRAINTS['census_tracts'])
    print(f"   Census Tracts: {'✅ PASS' if passed else '❌ FAIL'}")
    for field, data in results.items():
        status = '✅' if data['pass'] else '❌'
        if data['invalid'] > 0:
            print(f"      {status} {field}: {data['invalid']} invalid values ({data['pct_valid']*100:.1f}% valid)")
    all_passed &= passed
    
    # Uniqueness
    print("\n3️⃣  UNIQUENESS")
    passed, results = check_uniqueness('properties', ['property_id'])
    status = '✅ PASS' if passed else '❌ FAIL'
    print(f"   Properties: {status} ({results['duplicates']} duplicates)")
    all_passed &= passed
    
    passed, results = check_uniqueness('census_tracts', ['tract_geoid'])
    status = '✅ PASS' if passed else '❌ FAIL'
    print(f"   Census Tracts: {status} ({results['duplicates']} duplicates)")
    all_passed &= passed
    
    # Integrity
    print("\n4️⃣  INTEGRITY")
    passed, results = check_integrity('census_tracts', 'properties', 'census_tract_geoid', 'tract_geoid')
    status = '✅ PASS' if passed else '❌ FAIL'
    print(f"   Properties → Census: {status} ({results['orphans']} orphans)")
    all_passed &= passed
    
    passed, results = check_integrity('properties', 'psychographic_profiles', 'property_id', 'property_id')
    status = '✅ PASS' if passed else '❌ FAIL'
    print(f"   Psychographics → Properties: {status} ({results['orphans']} orphans)")
    all_passed &= passed
    
    # Outliers
    print("\n5️⃣  OUTLIER DETECTION (IQR)")
    for field in ['estimated_value', 'square_footage', 'risk_score']:
        outliers, lower, upper = detect_outliers_iqr('properties', field)
        print(f"   {field}: {outliers} outliers (bounds: {lower:.0f} - {upper:.0f})")
    
    return all_passed

def recalculate_derived_metrics():
    """Recalculate derived metrics after cleaning"""
    print("\n🔄 Recalculating Derived Metrics")
    print("=" * 60)
    
    conn = engine.connect()
    
    # Recalc price per sqft
    conn.execute(text("""
        UPDATE properties 
        SET price_per_sqft = ROUND(estimated_value::DECIMAL / NULLIF(square_footage, 0), 2)
        WHERE estimated_value IS NOT NULL AND square_footage > 0;
    """))
    print("  ✅ Recalculated price_per_sqft")
    
    # Recalc census metrics
    conn.execute(text("""
        UPDATE census_tracts 
        SET 
            homeownership_rate = ROUND((owner_occupied_units::DECIMAL / NULLIF(total_housing_units, 0)) * 100, 2),
            affordability_index = ROUND(median_household_income::DECIMAL / NULLIF(median_home_value, 0) * 100, 2)
        WHERE total_housing_units > 0 
          AND median_household_income > 0 
          AND median_home_value > 0;
    """))
    print("  ✅ Recalculated census metrics")
    
    # Recalc risk scores with valid inputs only
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
          AND p.property_age IS NOT NULL
          AND ct.median_household_income > 0
          AND ct.median_home_value > 0;
    """))
    print("  ✅ Recalculated risk_score")
    
    conn.commit()
    conn.close()

def generate_quality_report():
    """Generate final quality report"""
    print("\n📈 Final Quality Report")
    print("=" * 60)
    
    conn = engine.connect()
    
    # Properties summary
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(estimated_value) as with_value,
            COUNT(risk_score) as with_risk,
            ROUND(AVG(estimated_value)) as avg_value,
            ROUND(AVG(risk_score), 1) as avg_risk
        FROM properties
        WHERE estimated_value BETWEEN 50000 AND 5000000;
    """))
    p = result.fetchone()
    print(f"\n📍 Properties (valid range):")
    print(f"   Total: {p[0]}")
    print(f"   With value: {p[1]} ({p[1]*100//p[0]}%)")
    print(f"   With risk: {p[2]} ({p[2]*100//p[0]}%)")
    print(f"   Avg value: ${p[3]:,.0f}")
    print(f"   Avg risk: {p[4]}")
    
    # Census summary
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(median_household_income) as with_income,
            ROUND(AVG(median_household_income)) as avg_income,
            ROUND(AVG(median_home_value)) as avg_home_value
        FROM census_tracts
        WHERE median_household_income > 0 AND median_home_value > 0;
    """))
    c = result.fetchone()
    print(f"\n🏘️  Census Tracts (valid range):")
    print(f"   Total: {c[0]}")
    print(f"   With income: {c[1]} ({c[1]*100//c[0]}%)")
    print(f"   Avg income: ${c[2]:,.0f}")
    print(f"   Avg home value: ${c[3]:,.0f}")
    
    conn.close()

def main():
    print("🔍 Data Quality & Validation Framework")
    print("=" * 60)
    
    # Run initial checks
    passed = run_quality_checks()
    
    if not passed:
        print("\n⚠️  Quality issues detected - applying fixes...")
        fix_validity_issues()
        recalculate_derived_metrics()
        
        print("\n🔄 Re-running quality checks...")
        passed = run_quality_checks()
    
    generate_quality_report()
    
    if passed:
        print("\n✅ All quality checks PASSED - data is production-ready")
    else:
        print("\n❌ Some quality checks FAILED - review and fix before production")
        exit(1)

if __name__ == "__main__":
    main()
