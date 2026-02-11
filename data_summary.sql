-- Data Enrichment Summary Report
-- Generated: $(date)

\echo '========================================='
\echo 'STORMOPS DATA ENRICHMENT SUMMARY'
\echo '========================================='

\echo ''
\echo '📍 PROPERTIES'
SELECT 
    COUNT(*) as total_properties,
    COUNT(DISTINCT city) as cities,
    COUNT(DISTINCT zip_code) as zip_codes,
    COUNT(census_tract_geoid) as census_linked,
    ROUND(AVG(estimated_value)) as avg_value,
    ROUND(AVG(square_footage)) as avg_sqft,
    ROUND(AVG(price_per_sqft), 2) as avg_price_per_sqft,
    ROUND(AVG(risk_score), 2) as avg_risk_score
FROM properties;

\echo ''
\echo '🏘️  CENSUS TRACTS'
SELECT 
    COUNT(*) as total_tracts,
    ROUND(AVG(median_household_income)) as avg_income,
    ROUND(AVG(median_home_value)) as avg_home_value,
    ROUND(AVG(homeownership_rate), 2) as avg_homeownership_rate,
    ROUND(AVG(affordability_index), 2) as avg_affordability
FROM census_tracts;

\echo ''
\echo '🎯 PSYCHOGRAPHIC PERSONAS'
SELECT 
    primary_persona,
    COUNT(*) as count,
    ROUND(AVG(risk_tolerance), 2) as avg_risk_tolerance,
    ROUND(AVG(price_sensitivity), 2) as avg_price_sensitivity
FROM psychographic_profiles
GROUP BY primary_persona
ORDER BY count DESC;

\echo ''
\echo '⚠️  RISK DISTRIBUTION'
SELECT 
    CASE 
        WHEN risk_score < 40 THEN 'Low (0-39)'
        WHEN risk_score < 60 THEN 'Medium (40-59)'
        WHEN risk_score < 80 THEN 'High (60-79)'
        ELSE 'Very High (80+)'
    END as risk_category,
    COUNT(*) as property_count,
    ROUND(AVG(estimated_value)) as avg_value
FROM properties
WHERE risk_score IS NOT NULL
GROUP BY risk_category
ORDER BY MIN(risk_score);

\echo ''
\echo '🏠 PROPERTY TYPE DISTRIBUTION'
SELECT 
    property_type,
    COUNT(*) as count,
    ROUND(AVG(estimated_value)) as avg_value,
    ROUND(AVG(price_per_sqft), 2) as avg_price_per_sqft
FROM properties
GROUP BY property_type
ORDER BY count DESC;

\echo ''
\echo '========================================='
\echo 'DATA QUALITY METRICS'
\echo '========================================='

SELECT 
    'Properties' as entity,
    COUNT(*) as total,
    COUNT(address) as with_address,
    COUNT(census_tract_geoid) as with_census,
    COUNT(risk_score) as with_risk,
    COUNT(estimated_value) as with_value
FROM properties
UNION ALL
SELECT 
    'Census Tracts',
    COUNT(*),
    COUNT(median_household_income),
    COUNT(homeownership_rate),
    COUNT(affordability_index),
    COUNT(median_home_value)
FROM census_tracts
UNION ALL
SELECT 
    'Psychographic Profiles',
    COUNT(*),
    COUNT(primary_persona),
    COUNT(risk_tolerance),
    COUNT(price_sensitivity),
    COUNT(calculated_at)
FROM psychographic_profiles;
