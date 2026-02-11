"""
Psychological Profiling and Lead Scoring Service
Integrates with voice operations for persona-based targeting
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersonaType(Enum):
    REALIST = "realist"
    SKEPTIC = "skeptic"
    VISIONARY = "visionary"
    URGENT = "urgent"
    QUALITY = "quality"


@dataclass
class PersonaProfile:
    name: str
    hooks: List[str]
    pain_points: List[str]
    communication_style: str
    decision_factors: List[str]
    script_tone: str
    disqualifiers: List[str]
    conversion_triggers: List[str]
    avg_cycle_days: int
    price_sensitivity: float


PERSONA_PROFILES = {
    PersonaType.REALIST: PersonaProfile(
        name="Realist",
        hooks=[
            "BBA Accredited No.3",
            "5yr array warranties",
            "Licensed & insured",
            "Same-week availability",
            "Written estimates",
        ],
        pain_points=[
            "Hidden costs",
            "Unreliable contractors",
            "Communication gaps",
            "Timeline delays",
        ],
        communication_style="Professional, data-driven, authoritative",
        decision_factors=[
            "Credentials",
            "Warranty terms",
            "Timeline",
            "Price transparency",
        ],
        script_tone="Direct, factual, no fluff",
        disqualifiers=[
            "just looking",
            "thinking about it",
            "not interested",
            "maybe later",
        ],
        conversion_triggers=[
            "free inspection",
            "same week availability",
            "written estimate",
            "no obligation",
        ],
        avg_cycle_days=7,
        price_sensitivity=0.6,
    ),
    PersonaType.SKEPTIC: PersonaProfile(
        name="Skeptic",
        hooks=[
            "$0 commencement",
            "Up to 23% financing",
            "No hidden fees",
            "Price match guarantee",
            "Flexible payments",
        ],
        pain_points=[
            "High upfront costs",
            "Fear of overpaying",
            "Aggressive sales tactics",
            "Regret after purchase",
        ],
        communication_style="Empathetic, transparent, reassuring",
        decision_factors=["Price", "Financing options", "Reviews", "Trust signals"],
        script_tone="Understanding, patient, no pressure",
        disqualifiers=[
            "too expensive",
            "can't afford",
            "need to consult spouse",
            "not in budget",
        ],
        conversion_triggers=[
            "financing options",
            "payment plans",
            "price match",
            "money-back guarantee",
            "0 down",
        ],
        avg_cycle_days=14,
        price_sensitivity=0.9,
    ),
    PersonaType.VISIONARY: PersonaProfile(
        name="Visionary",
        hooks=[
            "Lifetime transferability",
            "Aging roof blueprints",
            "Home value increase",
            "Energy efficiency",
            "Curb appeal",
        ],
        pain_points=[
            "Making wrong choice",
            "Short-term thinking",
            "Missing opportunities",
            "Regret on quality",
        ],
        communication_style="Inspirational, long-term focused, consultative",
        decision_factors=[
            "Long-term value",
            "Quality",
            "Aesthetics",
            "Future benefits",
        ],
        script_tone="Big-picture, consultative, aspirational",
        disqualifiers=["not now", "maybe later", "future project", "not a priority"],
        conversion_triggers=[
            "energy savings",
            "curb appeal",
            "resale value",
            "lifetime warranty",
            "smart investment",
        ],
        avg_cycle_days=21,
        price_sensitivity=0.4,
    ),
    PersonaType.URGENT: PersonaProfile(
        name="Urgent",
        hooks=[
            "Storm damage emergency",
            "Leak response",
            "Immediate availability",
            "24/7 emergency line",
            "Quick turnaround",
        ],
        pain_points=[
            "Water damage spread",
            "Insurance deadlines",
            "Temporary living situation",
            "Property devaluation",
        ],
        communication_style="Urgent, action-oriented, reassuring",
        decision_factors=[
            "Speed",
            "Emergency response",
            "Immediate action",
            "Problem resolution",
        ],
        script_tone="Fast, direct, calming",
        disqualifiers=["can wait", "not urgent", "later is fine", "whenever"],
        conversion_triggers=[
            "same day service",
            "emergency response",
            "temporary fix",
            "immediate assessment",
            "stop the leak",
        ],
        avg_cycle_days=2,
        price_sensitivity=0.3,
    ),
    PersonaType.QUALITY: PersonaProfile(
        name="Quality",
        hooks=[
            "Premium materials",
            "Certified installers",
            "Best-in-class warranty",
            "Industry experience",
            "Manufacturer certified",
        ],
        pain_points=[
            "Subpar workmanship",
            "Cheap materials",
            " warranty void",
            "Future repairs",
        ],
        communication_style="Premium, quality-focused, detailed",
        decision_factors=[
            "Quality",
            "Craftsmanship",
            "Certifications",
            "Warranty strength",
        ],
        script_tone="Professional, detailed, confident",
        disqualifiers=[
            "cheapest option",
            "whatever is fastest",
            "lowest price",
            "deal of the day",
        ],
        conversion_triggers=[
            "premium materials",
            "extended warranty",
            "certified work",
            "best-in-class",
            "manufacturer certified",
        ],
        avg_cycle_days=14,
        price_sensitivity=0.5,
    ),
}


@dataclass
class LeadPsychProfile:
    lead_id: str
    primary_persona: PersonaType
    secondary_persona: Optional[PersonaType]
    confidence_scores: Dict[PersonaType, float]
    triggers_identified: List[str]
    pain_points_identified: List[str]
    optimal_contact_time: str
    recommended_script: str
    disqualifier_risk: List[str]
    conversion_probability: float
    last_updated: datetime = field(default_factory=datetime.utcnow)


class PsychologicalProfilingService:
    """Analyzes lead behavior and assigns psychological profiles"""

    def __init__(self):
        self.profiles = PERSONA_PROFILES

    def analyze_lead_behavior(self, lead_data: Dict) -> LeadPsychProfile:
        """Analyze lead behavior and determine psychological profile"""

        signals = self._extract_signals(lead_data)
        persona_scores = self._score_personas(signals)
        primary_persona = max(
            persona_scores.keys(), key=lambda k: float(persona_scores.get(k, 0))
        )
        secondary_persona = self._get_secondary_persona(persona_scores)

        profile = self.profiles[primary_persona]

        return LeadPsychProfile(
            lead_id=lead_data.get("id", ""),
            primary_persona=primary_persona,
            secondary_persona=secondary_persona,
            confidence_scores=persona_scores,
            triggers_identified=self._identify_triggers(lead_data, primary_persona),
            pain_points_identified=self._identify_pain_points(
                lead_data, primary_persona
            ),
            optimal_contact_time=self._determine_optimal_contact(lead_data),
            recommended_script=self._select_script_type(lead_data),
            disqualifier_risk=self._assess_disqualifier_risk(
                lead_data, primary_persona
            ),
            conversion_probability=self._calculate_conversion_probability(
                persona_scores, lead_data
            ),
        )

    def _extract_signals(self, lead_data: Dict) -> Dict[str, Any]:
        """Extract behavioral signals from lead data"""
        signals = {
            "inquiry_type": lead_data.get("inquiry_type", ""),
            "mentions_price": any(
                kw in str(lead_data).lower()
                for kw in ["price", "cost", "how much", "quote", "estimate"]
            ),
            "mentions_emergency": any(
                kw in str(lead_data).lower()
                for kw in ["leak", "emergency", "urgent", "now", "today"]
            ),
            "mentions_quality": any(
                kw in str(lead_data).lower()
                for kw in ["best", "quality", "premium", "certified"]
            ),
            "mentions_financing": any(
                kw in str(lead_data).lower()
                for kw in ["financing", "payment", " afford", "budget"]
            ),
            "mentions_warranty": any(
                kw in str(lead_data).lower()
                for kw in ["warranty", "guarantee", "coverage"]
            ),
            "mentions_value": any(
                kw in str(lead_data).lower()
                for kw in ["value", "investment", "resale", "energy"]
            ),
            "property_value_estimate": lead_data.get("property_value", 0),
            "roof_age": lead_data.get("roof_age", 0),
            "previous_claims": lead_data.get("previous_claims", 0),
            "response_speed": lead_data.get("response_speed", "normal"),
            "contact_history": lead_data.get("contact_history", []),
            "email_engagement": lead_data.get("email_engagement", {}),
            "source": lead_data.get("source", ""),
        }
        return signals

    def _score_personas(self, signals: Dict) -> Dict[PersonaType, float]:
        """Score each persona based on signals"""
        scores = {pt: 0.0 for pt in PersonaType}

        inquiry = signals.get("inquiry_type", "").lower()
        if "emergency" in inquiry or "leak" in inquiry:
            scores[PersonaType.URGENT] += 0.4
        if "price" in inquiry or signals["mentions_price"]:
            scores[PersonaType.SKEPTIC] += 0.3
        if "warranty" in inquiry or signals["mentions_warranty"]:
            scores[PersonaType.QUALITY] += 0.2
        if "value" in inquiry or signals["mentions_value"]:
            scores[PersonaType.VISIONARY] += 0.2
        if signals["mentions_emergency"]:
            scores[PersonaType.URGENT] += 0.3
        if signals["mentions_price"]:
            scores[PersonaType.SKEPTIC] += 0.2
        if signals["mentions_quality"]:
            scores[PersonaType.QUALITY] += 0.3
        if signals["mentions_financing"]:
            scores[PersonaType.SKEPTIC] += 0.25
        if signals["mentions_value"]:
            scores[PersonaType.VISIONARY] += 0.25
        if signals["mentions_warranty"]:
            scores[PersonaType.REALIST] += 0.2
            scores[PersonaType.QUALITY] += 0.15

        property_value = signals.get("property_value_estimate", 0)
        if property_value > 500000:
            scores[PersonaType.QUALITY] += 0.15
            scores[PersonaType.VISIONARY] += 0.1
        elif property_value < 250000:
            scores[PersonaType.SKEPTIC] += 0.15

        roof_age = signals.get("roof_age", 0)
        if roof_age > 15:
            scores[PersonaType.URGENT] += 0.1
            scores[PersonaType.VISIONARY] += 0.1
        elif roof_age < 5:
            scores[PersonaType.QUALITY] += 0.1

        previous_claims = signals.get("previous_claims", 0)
        if previous_claims > 0:
            scores[PersonaType.QUALITY] += 0.15
            scores[PersonaType.REALIST] += 0.1

        response_speed = signals.get("response_speed", "normal")
        if response_speed == "immediate":
            scores[PersonaType.URGENT] += 0.3
        elif response_speed == "slow":
            scores[PersonaType.SKEPTIC] += 0.1

        source = signals.get("source", "").lower()
        if "referral" in source:
            scores[PersonaType.VISIONARY] += 0.1
        elif "paid" in source or "ads" in source:
            scores[PersonaType.SKEPTIC] += 0.15

        for pt in PersonaType:
            scores[pt] = min(1.0, scores[pt])

        return scores

    def _get_secondary_persona(
        self, scores: Dict[PersonaType, float]
    ) -> Optional[PersonaType]:
        """Get secondary persona with next highest score"""
        sorted_scores = sorted(scores.items(), key=lambda x: float(x[1]), reverse=True)
        if len(sorted_scores) > 1 and float(sorted_scores[1][1]) > 0.3:
            return sorted_scores[1][0]
        return None

    def _identify_triggers(self, lead_data: Dict, persona: PersonaType) -> List[str]:
        """Identify conversion triggers for this lead based on persona"""
        profile = self.profiles[persona]
        triggers = []

        for trigger in profile.conversion_triggers:
            if any(trigger in str(v).lower() for v in lead_data.values()):
                triggers.append(trigger)

        return triggers[:5]

    def _identify_pain_points(self, lead_data: Dict, persona: PersonaType) -> List[str]:
        """Identify pain points for this lead based on persona"""
        profile = self.profiles[persona]

        pain_points = []
        for pain in profile.pain_points:
            if any(pain.split()[0] in str(v).lower() for v in lead_data.values()):
                pain_points.append(pain)

        return pain_points[:3]

    def _determine_optimal_contact(self, lead_data: Dict) -> str:
        """Determine optimal contact time based on lead behavior"""
        contact_history = lead_data.get("contact_history", [])

        if not contact_history:
            return "morning"

        successful_contacts = [
            c for c in contact_history if c.get("result") == "connected"
        ]
        if not successful_contacts:
            return "morning"

        hour_counts = {}
        for contact in successful_contacts:
            hour = contact.get("hour", 10)
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        best_hour = max(hour_counts.keys(), key=lambda h: hour_counts.get(h, 0))

        if 8 <= best_hour < 12:
            return "morning"
        elif 12 <= best_hour < 14:
            return "lunch"
        elif 14 <= best_hour < 17:
            return "afternoon"
        else:
            return "evening"

    def _select_script_type(self, lead_data: Dict) -> str:
        """Select appropriate script type based on lead analysis"""
        inquiry_type = lead_data.get("inquiry_type", "").lower()

        if "leak" in inquiry_type or "emergency" in inquiry_type:
            return "leak_emergency"
        elif "claim" in inquiry_type or "insurance" in inquiry_type:
            return "insurance_claim"
        elif "referral" in inquiry_type:
            return "referral_thanks"
        elif "warranty" in inquiry_type:
            return "warranty_check"
        else:
            return "initial_outbound"

    def _assess_disqualifier_risk(
        self, lead_data: Dict, persona: PersonaType
    ) -> List[str]:
        """Assess risk of disqualification based on persona"""
        profile = self.profiles[persona]
        content = " ".join(str(v).lower() for v in lead_data.values())

        disqualifiers = []
        for dq in profile.disqualifiers:
            if any(word in content for word in dq.split()):
                disqualifiers.append(dq)

        return disqualifiers

    def _calculate_conversion_probability(
        self, scores: Dict[PersonaType, float], lead_data: Dict
    ) -> float:
        """Calculate overall conversion probability"""
        base_probability = 0.25

        top_persona_score = max(float(v) for v in scores.values())
        base_probability += top_persona_score * 0.3

        storm_risk = lead_data.get("storm_risk_score", 0)
        base_probability += storm_risk * 0.2

        if lead_data.get("has_insurance_claim"):
            base_probability += 0.15

        if lead_data.get("property_value", 0) > 400000:
            base_probability += 0.05

        response_speed = lead_data.get("response_speed", "normal")
        if response_speed == "immediate":
            base_probability += 0.1
        elif response_speed == "slow":
            base_probability -= 0.05

        return min(0.95, max(0.05, base_probability))


class VoiceReadyLeadFilter:
    """Filters and scores leads for voice campaign eligibility"""

    def __init__(self, profiling_service: PsychologicalProfilingService):
        self.profiler = profiling_service

    def filter_voice_ready_leads(
        self, leads: List[Dict], max_leads: int = 100
    ) -> List[Dict]:
        """Filter and prioritize leads for voice campaigns"""

        voice_ready = []

        for lead in leads:
            if not self._is_voice_eligible(lead):
                continue

            profile = self.profiler.analyze_lead_behavior(lead)

            if profile.conversion_probability < 0.1:
                continue

            lead["voice_profile"] = {
                "persona": profile.primary_persona.value,
                "confidence": profile.confidence_scores[profile.primary_persona],
                "conversion_prob": profile.conversion_probability,
                "triggers": profile.triggers_identified,
                "disqualifier_risk": profile.disqualifier_risk,
                "optimal_contact": profile.optimal_contact_time,
                "script": profile.recommended_script,
            }

            voice_ready.append(lead)

        voice_ready.sort(
            key=lambda x: float(x.get("voice_profile", {}).get("conversion_prob", 0)),
            reverse=True,
        )

        return voice_ready[:max_leads]

    def _is_voice_eligible(self, lead: Dict) -> bool:
        """Check if lead is eligible for voice contact"""
        if not lead.get("phone"):
            return False

        if lead.get("do_not_call"):
            return False

        if lead.get("opted_out"):
            return False

        last_contact = lead.get("last_contact_date")
        if last_contact:
            last_contact_date = (
                datetime.fromisoformat(last_contact)
                if isinstance(last_contact, str)
                else last_contact
            )
            if datetime.utcnow() - last_contact_date < timedelta(hours=24):
                return False

        if lead.get("attempts_today", 0) >= 3:
            return False

        return True

    def batch_profile_leads(self, leads: List[Dict]) -> List[Dict]:
        """Profile multiple leads in batch"""
        profiled_leads = []

        for lead in leads:
            profile = self.profiler.analyze_lead_behavior(lead)

            lead["psych_profile"] = {
                "primary_persona": profile.primary_persona.value,
                "secondary_persona": profile.secondary_persona.value
                if profile.secondary_persona
                else None,
                "confidence_scores": {
                    k.value: v for k, v in profile.confidence_scores.items()
                },
                "triggers": profile.triggers_identified,
                "pain_points": profile.pain_points_identified,
                "optimal_contact": profile.optimal_contact_time,
                "script_type": profile.recommended_script,
                "disqualifier_risk": profile.disqualifier_risk,
                "conversion_probability": profile.conversion_probability,
                "persona_profile": {
                    "hooks": self.profiler.profiles[profile.primary_persona].hooks,
                    "script_tone": self.profiler.profiles[
                        profile.primary_persona
                    ].script_tone,
                    "decision_factors": self.profiler.profiles[
                        profile.primary_persona
                    ].decision_factors,
                },
            }

            profiled_leads.append(lead)

        return profiled_leads


def create_profiling_service() -> PsychologicalProfilingService:
    """Factory function to create profiling service"""
    return PsychologicalProfilingService()


if __name__ == "__main__":
    profiler = create_profiling_service()

    sample_leads = [
        {
            "id": "lead-001",
            "name": "John Smith",
            "phone": "+15551234567",
            "inquiry_type": "Emergency leak",
            "property_value": 450000,
            "roof_age": 12,
            "previous_claims": 1,
            "response_speed": "immediate",
            "storm_risk_score": 0.85,
        },
        {
            "id": "lead-002",
            "name": "Jane Doe",
            "phone": "+15559876543",
            "inquiry_type": "Price inquiry",
            "property_value": 280000,
            "roof_age": 8,
            "previous_claims": 0,
            "response_speed": "normal",
            "storm_risk_score": 0.45,
        },
    ]

    for lead in sample_leads:
        profile = profiler.analyze_lead_behavior(lead)
        print(f"\nLead: {lead['name']}")
        print(f"Primary Persona: {profile.primary_persona.value}")
        print(f"Confidence: {profile.confidence_scores[profile.primary_persona]:.2f}")
        print(f"Conversion Prob: {profile.conversion_probability:.2%}")
        print(f"Triggers: {profile.triggers_identified}")
