"""
CV Phase 1 → SII_v2
Add computer vision features to SII model
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, precision_score, classification_report
from sklearn.model_selection import train_test_split
import shap
import pickle

# Mock CV features (replace with real RoofD output)
def generate_cv_features(property_ids):
    """Generate mock CV features for pilot."""
    np.random.seed(42)
    return pd.DataFrame({
        'property_id': property_ids,
        'defect_count': np.random.poisson(3, len(property_ids)),
        'damage_area_pct': np.random.uniform(0, 0.3, len(property_ids)),
        'roof_wear_score': np.random.uniform(0, 1, len(property_ids)),
        'missing_shingles': np.random.poisson(2, len(property_ids)),
        'granule_loss_pct': np.random.uniform(0, 0.5, len(property_ids))
    })


def train_sii_v2():
    """Train SII_v2 with CV features."""
    
    # Load A-tier leads (SII_v1 features)
    leads = pd.read_csv('a_tier_leads.csv')
    
    # Add CV features
    cv_features = generate_cv_features(leads['property_id'])
    df = leads.merge(cv_features, on='property_id')
    
    # Original SII_v1 features
    v1_features = [
        'risk_score', 'estimated_value', 'property_age',
        'median_household_income', 'homeownership_rate',
        'risk_tolerance', 'price_sensitivity'
    ]
    
    # New CV features
    cv_feature_cols = [
        'defect_count', 'damage_area_pct', 'roof_wear_score',
        'missing_shingles', 'granule_loss_pct'
    ]
    
    # SII_v2 = v1 + CV
    v2_features = v1_features + cv_feature_cols
    
    # Target: conversion (from journeys)
    from sqlalchemy import create_engine, text
    engine = create_engine('sqlite:///stormops_journeys.db')
    
    with engine.connect() as conn:
        conversions = pd.read_sql(text("""
            SELECT property_id, MAX(CAST(converted AS INTEGER)) as converted
            FROM customer_journeys
            GROUP BY property_id
        """), conn)
    
    df = df.merge(conversions, on='property_id', how='left')
    df['converted'] = df['converted'].fillna(0).astype(int)
    
    # Train/test split
    X_v1 = df[v1_features].fillna(0)
    X_v2 = df[v2_features].fillna(0)
    y = df['converted']
    
    X_v1_train, X_v1_test, y_train, y_test = train_test_split(X_v1, y, test_size=0.3, random_state=42)
    X_v2_train, X_v2_test, _, _ = train_test_split(X_v2, y, test_size=0.3, random_state=42)
    
    # Train SII_v1 (baseline)
    print("Training SII_v1 (baseline)...")
    model_v1 = GradientBoostingClassifier(n_estimators=100, random_state=42)
    model_v1.fit(X_v1_train, y_train)
    
    y_pred_v1 = model_v1.predict(X_v1_test)
    y_proba_v1 = model_v1.predict_proba(X_v1_test)[:, 1]
    
    auc_v1 = roc_auc_score(y_test, y_proba_v1)
    precision_v1 = precision_score(y_test, y_pred_v1)
    
    # Train SII_v2 (with CV)
    print("Training SII_v2 (with CV features)...")
    model_v2 = GradientBoostingClassifier(n_estimators=100, random_state=42)
    model_v2.fit(X_v2_train, y_train)
    
    y_pred_v2 = model_v2.predict(X_v2_test)
    y_proba_v2 = model_v2.predict_proba(X_v2_test)[:, 1]
    
    auc_v2 = roc_auc_score(y_test, y_proba_v2)
    precision_v2 = precision_score(y_test, y_pred_v2)
    
    # Compare
    print("\n" + "=" * 60)
    print("MODEL COMPARISON")
    print("=" * 60)
    print(f"SII_v1 (baseline):")
    print(f"  AUC: {auc_v1:.4f}")
    print(f"  Precision: {precision_v1:.4f}")
    print(f"\nSII_v2 (with CV):")
    print(f"  AUC: {auc_v2:.4f}")
    print(f"  Precision: {precision_v2:.4f}")
    print(f"\nUplift:")
    print(f"  ΔAUC: {auc_v2 - auc_v1:+.4f} ({(auc_v2/auc_v1 - 1)*100:+.1f}%)")
    print(f"  ΔPrecision: {precision_v2 - precision_v1:+.4f} ({(precision_v2/precision_v1 - 1)*100:+.1f}%)")
    
    # SHAP analysis
    print("\nSHAP Feature Importance (SII_v2):")
    explainer = shap.TreeExplainer(model_v2)
    shap_values = explainer.shap_values(X_v2_test)
    
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # For binary classification
    
    feature_importance = pd.DataFrame({
        'feature': v2_features,
        'importance': np.abs(shap_values).mean(axis=0)
    }).sort_values('importance', ascending=False)
    
    print(feature_importance.head(10).to_string(index=False))
    
    # Save models
    with open('sii_v1_model.pkl', 'wb') as f:
        pickle.dump(model_v1, f)
    
    with open('sii_v2_model.pkl', 'wb') as f:
        pickle.dump(model_v2, f)
    
    print("\n✅ Models saved: sii_v1_model.pkl, sii_v2_model.pkl")
    
    # Decision: Use v2 if uplift > 5%
    if (auc_v2 - auc_v1) / auc_v1 > 0.05:
        print("\n🎯 DECISION: SII_v2 shows significant uplift (>5%)")
        print("   → Deploy SII_v2 as default")
        print("   → Scale CV inference across full territory")
        return 'v2', model_v2
    else:
        print("\n⚠️  DECISION: SII_v2 uplift < 5%")
        print("   → Keep SII_v1 as default")
        print("   → Revisit CV features or expand pilot")
        return 'v1', model_v1


def score_leads_with_sii_v2(model, leads_df):
    """Score all leads with SII_v2."""
    
    # Add CV features
    cv_features = generate_cv_features(leads_df['property_id'])
    df = leads_df.merge(cv_features, on='property_id')
    
    v2_features = [
        'risk_score', 'estimated_value', 'property_age',
        'median_household_income', 'homeownership_rate',
        'risk_tolerance', 'price_sensitivity',
        'defect_count', 'damage_area_pct', 'roof_wear_score',
        'missing_shingles', 'granule_loss_pct'
    ]
    
    X = df[v2_features].fillna(0)
    
    # Calibrated scoring: stretch probabilities to match A-tier expectations
    # Raw probability → Calibrated score
    raw_proba = model.predict_proba(X)[:, 1]
    
    # Calibration: Map [0.5, 1.0] probability → [70, 110] score
    # This matches A-tier mental model where high-confidence leads score 100+
    sii_v2_scores = 70 + (raw_proba - 0.5) * 80
    sii_v2_scores = np.clip(sii_v2_scores, 0, 110)
    
    df['sii_v2_score'] = sii_v2_scores
    
    return df[['property_id', 'sii_score', 'sii_v2_score']]


if __name__ == '__main__':
    print("=" * 60)
    print("CV PHASE 1 → SII_v2")
    print("=" * 60)
    
    # Train and compare
    version, model = train_sii_v2()
    
    if version == 'v2':
        print("\n" + "=" * 60)
        print("SCORING ALL LEADS WITH SII_v2")
        print("=" * 60)
        
        leads = pd.read_csv('a_tier_leads.csv')
        scored = score_leads_with_sii_v2(model, leads)
        
        print(f"\nScored {len(scored)} leads")
        print("\nSample scores:")
        print(scored.head(10).to_string(index=False))
        
        # Write to database
        from sqlalchemy import create_engine, text
        engine = create_engine('sqlite:///stormops_attribution.db')
        
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sii_v2_scores (
                    property_id TEXT PRIMARY KEY,
                    sii_v1_score FLOAT,
                    sii_v2_score FLOAT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            for _, row in scored.iterrows():
                conn.execute(text("""
                    INSERT OR REPLACE INTO sii_v2_scores 
                    (property_id, sii_v1_score, sii_v2_score)
                    VALUES (:pid, :v1, :v2)
                """), {
                    'pid': row['property_id'],
                    'v1': row['sii_score'],
                    'v2': row['sii_v2_score']
                })
        
        print("\n✅ SII_v2 scores written to database")
    
    print("\n" + "=" * 60)
    print("✅ CV Phase 1 complete")
    print("=" * 60)
