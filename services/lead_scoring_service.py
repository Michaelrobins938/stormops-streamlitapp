
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class ScoredLead:
    address: str
    zip_code: str
    roof_age: int
    score: float
    tags: List[str]
    confidence: float

class LeadScoringService:
    """Fusion Engine: Intersects Weather Data with Property Attributes."""

    def rank_leads(self, properties: List[Dict], max_hail: float) -> List[ScoredLead]:
        ranked = []
        for p in properties:
            base_risk = p["roof_age"] / 30.0
            storm_mult = min(1.0, max_hail / 3.0)
            final_score = (base_risk * 0.4) + (storm_mult * 0.6)
            final_score = max(0.01, min(0.99, final_score))

            tags = []
            if p["roof_age"] > 15: tags.append("OLD_ROOF")
            if final_score > 0.8: tags.append("HIGH_PRIORITY")

            ranked.append(ScoredLead(
                address=p["address"],
                zip_code=p["zip"],
                roof_age=p["roof_age"],
                score=round(final_score, 2),
                tags=tags,
                confidence=0.9,
            ))
        return sorted(ranked, key=lambda x: x.score, reverse=True)
