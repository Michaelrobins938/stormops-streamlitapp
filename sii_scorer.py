"""
StormOps Impact Index (SII) Scorer
Combines hail intensity, roof material, and roof age into a 0-100 damage probability score.
Based on physics-backed hail damage models.
"""

import math
from typing import Optional, Dict

class SIIScorer:
    """
    StormOps Impact Index: 0-100 scalar per roof.
    
    Inputs:
    - hail_intensity_mm: Hail diameter in mm (e.g., 25mm = 1", 64mm = 2.5")
    - roof_material: asphalt, metal, tile, wood, etc.
    - roof_age_years: Age of roof in years
    
    Output:
    - sii_score: 0-100 (0 = no damage, 100 = total loss)
    - damage_probability: 0-1 (probability of any damage)
    - estimated_claim_value_usd: Estimated claim value (requires roof area, not implemented here)
    """
    
    # Hail intensity thresholds (mm) for damage onset per material
    HAIL_DAMAGE_THRESHOLDS = {
        'asphalt': 20,      # ~0.8" hail starts damage
        'metal': 32,        # ~1.25" hail starts damage
        'tile': 38,         # ~1.5" hail starts damage
        'wood': 25,         # ~1" hail starts damage
        'composite': 22,    # ~0.9" hail starts damage
    }
    
    # Material vulnerability multipliers (higher = more vulnerable)
    MATERIAL_VULNERABILITY = {
        'asphalt': 1.0,     # Baseline
        'metal': 0.6,       # More resistant
        'tile': 0.7,        # Moderately resistant
        'wood': 1.2,        # More vulnerable
        'composite': 0.9,   # Slightly less vulnerable
    }
    
    # Age degradation: older roofs are more vulnerable
    # Multiplier increases with age (e.g., 20-year roof is 1.5x more vulnerable than new)
    AGE_DEGRADATION_RATE = 0.02  # 2% increase in vulnerability per year
    
    def __init__(self):
        pass
    
    def score(
        self,
        hail_intensity_mm: float,
        roof_material: str = 'asphalt',
        roof_age_years: int = 10,
    ) -> Dict[str, float]:
        """
        Compute SII score and damage probability.
        
        Args:
            hail_intensity_mm: Hail diameter in mm
            roof_material: Type of roof material
            roof_age_years: Age of roof in years
        
        Returns:
            Dict with keys: sii_score (0-100), damage_probability (0-1)
        """
        
        # Normalize material (lowercase, handle aliases)
        material = roof_material.lower().strip()
        if material not in self.MATERIAL_VULNERABILITY:
            material = 'asphalt'  # Default to asphalt if unknown
        
        # Get damage threshold for this material
        threshold_mm = self.HAIL_DAMAGE_THRESHOLDS.get(material, 20)
        
        # If hail is below threshold, no damage
        if hail_intensity_mm < threshold_mm:
            return {
                'sii_score': 0.0,
                'damage_probability': 0.0,
                'hail_intensity_mm': hail_intensity_mm,
                'roof_material': material,
                'roof_age_years': roof_age_years,
            }
        
        # Compute excess hail above threshold (mm)
        excess_hail_mm = hail_intensity_mm - threshold_mm
        
        # Base damage probability: sigmoid curve
        # Excess hail of 10mm above threshold → ~50% damage probability
        # Excess hail of 20mm above threshold → ~95% damage probability
        base_damage_prob = 1.0 / (1.0 + math.exp(-0.3 * excess_hail_mm))
        
        # Apply material vulnerability multiplier
        material_mult = self.MATERIAL_VULNERABILITY.get(material, 1.0)
        
        # Apply age degradation: older roofs are more vulnerable
        age_mult = 1.0 + (self.AGE_DEGRADATION_RATE * roof_age_years)
        
        # Combined damage probability
        damage_probability = min(base_damage_prob * material_mult * age_mult, 1.0)
        
        # Convert to 0-100 SII score
        sii_score = damage_probability * 100.0
        
        return {
            'sii_score': round(sii_score, 2),
            'damage_probability': round(damage_probability, 3),
            'hail_intensity_mm': hail_intensity_mm,
            'roof_material': material,
            'roof_age_years': roof_age_years,
            'material_multiplier': round(material_mult, 2),
            'age_multiplier': round(age_mult, 2),
        }
    
    def batch_score(self, parcels: list) -> list:
        """
        Score multiple parcels.
        
        Args:
            parcels: List of dicts with keys: hail_intensity_mm, roof_material, roof_age_years
        
        Returns:
            List of dicts with SII scores
        """
        results = []
        for parcel in parcels:
            result = self.score(
                hail_intensity_mm=parcel.get('hail_intensity_mm', 0),
                roof_material=parcel.get('roof_material', 'asphalt'),
                roof_age_years=parcel.get('roof_age_years', 10),
            )
            result['parcel_id'] = parcel.get('parcel_id')
            results.append(result)
        return results


# Example usage
if __name__ == '__main__':
    scorer = SIIScorer()
    
    # Test cases
    test_cases = [
        {'hail_intensity_mm': 15, 'roof_material': 'asphalt', 'roof_age_years': 5},  # Below threshold
        {'hail_intensity_mm': 25, 'roof_material': 'asphalt', 'roof_age_years': 5},  # 1" hail, new roof
        {'hail_intensity_mm': 25, 'roof_material': 'asphalt', 'roof_age_years': 20}, # 1" hail, old roof
        {'hail_intensity_mm': 64, 'roof_material': 'asphalt', 'roof_age_years': 10}, # 2.5" hail
        {'hail_intensity_mm': 64, 'roof_material': 'metal', 'roof_age_years': 10},   # 2.5" hail, metal
    ]
    
    for case in test_cases:
        result = scorer.score(**case)
        print(f"Hail: {case['hail_intensity_mm']}mm, Material: {case['roof_material']}, Age: {case['roof_age_years']}y")
        print(f"  SII: {result['sii_score']}, Damage Prob: {result['damage_probability']}\n")
