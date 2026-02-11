"""
Retell.ai Voice Agent Service for StormOps Platform
Provides autonomous voice automation for roofing lead generation and customer engagement
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import re

import httpx
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

RETELL_API_BASE = "https://api.retellai.com"
RETELL_llM_BASE = "https://api.retellai.com/v1"


class CallStatus(Enum):
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"


class LeadPersona(Enum):
    REALIST = "realist"
    SKEPTIC = "skeptic"
    VISIONARY = "visionary"
    URGENT = "urgent"
    QUALITY = "quality"


class IntentType(Enum):
    LEAK_INQUIRY = "leak_inquiry"
    WARRANTY_CHECK = "warranty_check"
    HOA_CONTACT = "hoa_contact"
    SCHEDULE_INSPECTION = "schedule_inspection"
    PRICE_QUESTION = "price_question"
    INSURANCE_CLAIM = "insurance_claim"
    REFERRAL_REQUEST = "referral_request"
    CANCEL = "cancel"
    UNKNOWN = "unknown"


@dataclass
class VoiceCall:
    id: str
    lead_id: str
    phone_number: str
    status: CallStatus
    persona: LeadPersona
    intent_detected: Optional[IntentType] = None
    transcript: Optional[str] = None
    sentiment_score: Optional[float] = None
    disposition: Optional[str] = None
    callback_scheduled: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: int = 0
    retell_call_id: Optional[str] = None


@dataclass
class PersonaProfile:
    persona: LeadPersona
    hooks: List[str]
    cadence: str
    script_tone: str
    disqualifiers: List[str]
    conversion_triggers: List[str]


PERSONA_PROFILES = {
    LeadPersona.REALIST: PersonaProfile(
        persona=LeadPersona.REALIST,
        hooks=["BBA Accredited No.3", "5yr array warranties", "Licensed & insured"],
        cadence="Immediate timelines",
        script_tone="Professional, data-driven, authoritative",
        disqualifiers=["just looking", "thinking about it", "not interested"],
        conversion_triggers=[
            "free inspection",
            "same week availability",
            "written estimate",
        ],
    ),
    LeadPersona.SKEPTIC: PersonaProfile(
        persona=LeadPersona.SKEPTIC,
        hooks=["$0 commencement", "Up to 23% financing", "No hidden fees"],
        cadence="Introductory review cycle",
        script_tone="Empathetic, transparent, reassuring",
        disqualifiers=["too expensive", "can't afford", "need to consult spouse"],
        conversion_triggers=["financing options", "payment plans", "price match"],
    ),
    LeadPersona.VISIONARY: PersonaProfile(
        persona=LeadPersona.VISIONARY,
        hooks=[
            "Lifetime transferability",
            "Aging roof blueprints",
            "Home value increase",
        ],
        cadence="Quarterly portfolio review",
        script_tone="Inspirational, long-term focused, consultative",
        disqualifiers=["not now", "maybe later", "future project"],
        conversion_triggers=["energy savings", " curb appeal", "resale value"],
    ),
    LeadPersona.URGENT: PersonaProfile(
        persona=LeadPersona.URGENT,
        hooks=["Storm damage emergency", "Leak response", "Immediate availability"],
        cadence="Immediate response",
        script_tone="Urgent, action-oriented, reassuring",
        disqualifiers=["can wait", "not urgent", "later is fine"],
        conversion_triggers=["same day service", "emergency response", "temporary fix"],
    ),
    LeadPersona.QUALITY: PersonaProfile(
        persona=LeadPersona.QUALITY,
        hooks=["Premium materials", "Certified installers", "Best-in-class warranty"],
        cadence="Quality assessment cycle",
        script_tone="Premium, quality-focused, detailed",
        disqualifiers=["cheapest option", "whatever is fastest"],
        conversion_triggers=[
            "premium materials",
            "extended warranty",
            "certified work",
        ],
    ),
}

SCRIPT_TEMPLATES = {
    "initial_outbound": """Hello! This is {agent_name} from StormOps Roofing. I'm calling regarding the recent storm that impacted your area. We specialize in helping homeowners with storm damage assessments and insurance claim navigation. 

Do you have a moment to discuss how we can help protect your property?""",
    "leak_emergency": """Hello! This is {agent_name} from StormOps Roofing. We received your inquiry about a potential roof leak. Our team specializes in emergency leak response and can typically be at your location within hours. 

Would you like me to connect you with our emergency response team right away?""",
    "insurance_claim": """Hello! This is {agent_name} from StormOps Roofing. I'm calling to help you navigate your insurance claim for the recent storm damage. We work directly with all major insurance providers and can help ensure you receive the maximum coverage you're entitled to.

Have you filed your claim yet, or would you like guidance on the process?""",
    "follow_up": """Hello! This is {agent_name} from StormOps Roofing. I'm following up on our previous conversation about your roofing needs. We have availability next week for a free, no-obligation inspection.

Would Tuesday or Thursday work better for you?""",
    "referral_thanks": """Hello! This is {agent_name} from StormOps Roofing. Thank you for referring {referrer_name} to us! As a token of our appreciation, we want to offer you a {reward} credit toward your next service.

Would you like to schedule your free inspection to redeem this offer?""",
    "warranty_check": """Hello! This is {agent_name} from StormOps Roofing. I'm calling regarding your current roof warranty. We can help you understand what's covered and ensure your warranty remains valid with proper documentation.

Do you have your warranty information available?""",
}


class RetellVoiceService:
    def __init__(self, api_key: str, engine=None):
        self.api_key = api_key
        self.engine = engine or create_engine("sqlite:///stormops.db")
        SessionLocal = sessionmaker(bind=self.engine)
        self.db_session = SessionLocal
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self._ensure_tables()

    def _ensure_tables(self):
        Base.metadata.create_all(self.engine)

    async def create_voice_agent(
        self, name: str, llm_prompt: str, voice_id: str = "af_heart"
    ) -> Dict:
        """Create a new Retell AI voice agent"""
        try:
            response = await self.http_client.post(
                f"{RETELL_llM_BASE}/create-agent",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "name": name,
                    "llm_prompt": llm_prompt,
                    "voice_id": voice_id,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "voice_speed": 1.0,
                    "voice_pitch": 0.0,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create voice agent: {e}")
            raise

    async def initiate_outbound_call(
        self,
        lead_id: str,
        phone_number: str,
        campaign_type: str = "initial_outbound",
        persona: LeadPersona = LeadPersona.REALIST,
    ) -> VoiceCall:
        """Initiate an outbound voice call to a lead"""
        call_id = self._generate_call_id(lead_id, phone_number)

        script = self._get_script_for_campaign(campaign_type, persona)
        persona_profile = PERSONA_PROFILES[persona]

        llm_prompt = self._build_llm_prompt(persona_profile, script)

        try:
            response = await self.http_client.post(
                f"{RETELL_llM_BASE}/create-call",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "from_number": "+15551234567",
                    "to_number": phone_number,
                    "llm_prompt": llm_prompt,
                    "voice_id": "af_heart",
                    "agent_name": "StormOps_Roofing_Agent",
                    "max_duration": 300,
                    "poling_interval": 5,
                    "background_audio": "office",
                    "model": "gpt-4",
                },
            )
            response.raise_for_status()
            retell_call_id = response.json().get("call_id")

            call = VoiceCall(
                id=call_id,
                lead_id=lead_id,
                phone_number=phone_number,
                status=CallStatus.INITIATED,
                persona=persona,
                retell_call_id=retell_call_id,
            )

            self._save_call_to_db(call)
            return call

        except Exception as e:
            logger.error(f"Failed to initiate call: {e}")
            failed_call = VoiceCall(
                id=call_id,
                lead_id=lead_id,
                phone_number=phone_number,
                status=CallStatus.FAILED,
                persona=persona,
            )
            self._save_call_to_db(failed_call)
            raise

    def _build_llm_prompt(self, persona_profile: PersonaProfile, script: str) -> str:
        """Build the LLM prompt for the voice agent based on persona"""
        return f"""You are a professional roofing sales representative from StormOps Roofing. 

PERSONA: {persona_profile.script_tone}

KEY HOOKS TO MENTION: {", ".join(persona_profile.hooks)}

COMMUNICATION CADENCE: {persona_profile.cadence}

CONVERSION TRIGGERS TO HIGHLIGHT: {", ".join(persona_profile.conversion_triggers)}

DISQUALIFIERS (if homeowner says these, politely end call): {", ".join(persona_profile.disqualifiers)}

SCRIPT FRAMEWORK:
{script}

INSTRUCTIONS:
1. Greet warmly and introduce yourself
2. Mention the relevant hooks based on homeowner's responses
3. Identify intent keywords: "leak", "warranty", "HOA", "insurance", "price", "emergency"
4. Qualify the lead using the {persona_profile.persona.value} approach
5. Schedule callback or appointment if qualified
6. Always thank them for their time

Keep responses concise (under 2 sentences) and conversational. Never be pushy or aggressive."""

    def _get_script_for_campaign(self, campaign_type: str, persona: LeadPersona) -> str:
        """Get the appropriate script template for the campaign"""
        base_script = SCRIPT_TEMPLATES.get(
            campaign_type, SCRIPT_TEMPLATES["initial_outbound"]
        )

        persona_script_overrides = {
            LeadPersona.REALIST: "Focus on credentials, warranties, and immediate availability.",
            LeadPersona.SKEPTIC: "Emphasize financing options, no upfront costs, and transparency.",
            LeadPersona.VISIONARY: "Highlight long-term value, home improvement benefits, and quality materials.",
            LeadPersona.URGENT: "Acknowledge the emergency, promise rapid response, and immediate action.",
            LeadPersona.QUALITY: "Emphasize premium materials, certified installers, and comprehensive warranties.",
        }

        return f"{base_script}\n\n{persona_script_overrides.get(persona, '')}"

    async def process_voice_input(self, call_id: str, transcript: str) -> Dict:
        """Process voice input and return AI response"""
        intent = self._detect_intent(transcript)
        sentiment = self._analyze_sentiment(transcript)
        disposition = self._determine_disposition(intent, sentiment)

        response = {
            "intent": intent.value,
            "sentiment_score": sentiment,
            "disposition": disposition,
            "recommended_action": self._get_recommended_action(intent, sentiment),
        }

        self._update_call_transcript(
            call_id, transcript, intent, sentiment, disposition
        )

        return response

    def _detect_intent(self, transcript: str) -> IntentType:
        """Detect intent from voice transcript"""
        transcript_lower = transcript.lower()

        intent_keywords = {
            IntentType.LEAK_INQUIRY: [
                "leak",
                "water",
                "dripping",
                "ceiling stain",
                "water damage",
            ],
            IntentType.WARRANTY_CHECK: ["warranty", "guarantee", "coverage", "policy"],
            IntentType.HOA_CONTACT: [
                "hoa",
                "homeowners association",
                "approval",
                "restriction",
            ],
            IntentType.SCHEDULE_INSPECTION: [
                "inspection",
                "look at",
                "assess",
                "check",
                "evaluate",
            ],
            IntentType.PRICE_QUESTION: [
                "price",
                "cost",
                "how much",
                "quote",
                "estimate",
            ],
            IntentType.INSURANCE_CLAIM: ["insurance", "claim", "adjuster", "coverage"],
            IntentType.REFERRAL_REQUEST: ["referral", "recommend", "friend", "family"],
            IntentType.CANCEL: ["not interested", "cancel", "remove", "don't call"],
        }

        for intent, keywords in intent_keywords.items():
            if any(keyword in transcript_lower for keyword in keywords):
                return intent

        return IntentType.UNKNOWN

    def _analyze_sentiment(self, transcript: str) -> float:
        """Analyze sentiment of transcript (-1 to 1 scale)"""
        positive_words = [
            "yes",
            "interested",
            "great",
            "wonderful",
            "love",
            "excellent",
            "sure",
            "definitely",
            "absolutely",
        ]
        negative_words = [
            "no",
            "not",
            "don't",
            "never",
            "can't",
            "won't",
            "expensive",
            "busy",
            "later",
        ]

        words = transcript.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)

        if positive_count + negative_count == 0:
            return 0.0

        sentiment = (positive_count - negative_count) / (
            positive_count + negative_count
        )
        return max(-1.0, min(1.0, sentiment))

    def _determine_disposition(self, intent: IntentType, sentiment: float) -> str:
        """Determine call disposition based on intent and sentiment"""
        if intent == IntentType.CANCEL:
            return "DO_NOT_CALL"
        elif (
            intent in [IntentType.LEAK_INQUIRY, IntentType.INSURANCE_CLAIM]
            and sentiment > 0
        ):
            return "QUALIFIED_HOT"
        elif intent == IntentType.SCHEDULE_INSPECTION:
            return "SCHEDULED"
        elif intent == IntentType.PRICE_QUESTION:
            return "PRICE_SHOPPING"
        elif sentiment < -0.3:
            return "NOT_INTERESTED"
        else:
            return "FOLLOW_UP"

    def _get_recommended_action(self, intent: IntentType, sentiment: float) -> str:
        """Get recommended action based on intent and sentiment"""
        action_matrix = {
            (
                IntentType.LEAK_INQUIRY,
                0.5,
            ): "Dispatch emergency response team within 2 hours",
            (IntentType.LEAK_INQUIRY, -0.5): "Schedule leak inspection within 48 hours",
            (
                IntentType.INSURANCE_CLAIM,
                0.5,
            ): "Connect with insurance claims specialist",
            (
                IntentType.INSURANCE_CLAIM,
                -0.5,
            ): "Send insurance navigation guide via SMS",
            (IntentType.SCHEDULE_INSPECTION, 0.5): "Book appointment for tomorrow",
            (IntentType.SCHEDULE_INSPECTION, -0.5): "Send calendar link for scheduling",
            (
                IntentType.PRICE_QUESTION,
                0.5,
            ): "Prepare custom quote with financing options",
            (IntentType.PRICE_QUESTION, -0.5): "Send competitive comparison guide",
            (IntentType.REFERRAL_REQUEST, 0.5): "Process referral bonus immediately",
            (
                IntentType.WARRANTY_CHECK,
                0.5,
            ): "Pull warranty records and schedule review",
            (IntentType.UNKNOWN, 0.0): "Add to nurture campaign",
        }

        return action_matrix.get((intent, sentiment), "Manual review required")

    def _generate_call_id(self, lead_id: str, phone_number: str) -> str:
        """Generate unique call ID"""
        unique_string = f"{lead_id}-{phone_number}-{datetime.utcnow().isoformat()}"
        return f"CALL-{hashlib.md5(unique_string.encode()).hexdigest()[:12].upper()}"

    def _save_call_to_db(self, call: VoiceCall):
        """Save call record to database"""
        with self.engine.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO voice_calls (
                    id, lead_id, phone_number, status, persona,
                    intent_detected, transcript, sentiment_score,
                    disposition, callback_scheduled, created_at,
                    completed_at, duration_seconds, retell_call_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    call.id,
                    call.lead_id,
                    call.phone_number,
                    call.status.value,
                    call.persona.value,
                    call.intent_detected.value if call.intent_detected else None,
                    call.transcript,
                    call.sentiment_score,
                    call.disposition,
                    call.callback_scheduled.isoformat()
                    if call.callback_scheduled
                    else None,
                    call.created_at.isoformat(),
                    call.completed_at.isoformat() if call.completed_at else None,
                    call.duration_seconds,
                    call.retell_call_id,
                ),
            )
            conn.commit()

    def _update_call_transcript(
        self,
        call_id: str,
        transcript: str,
        intent: IntentType,
        sentiment: float,
        disposition: str,
    ):
        """Update call with transcript and analysis"""
        with self.engine.connect() as conn:
            existing = conn.execute(
                "SELECT transcript FROM voice_calls WHERE id = ?", (call_id,)
            ).fetchone()

            new_transcript = (
                f"{existing[0] or ''}\n[USER]: {transcript}"
                if existing
                else f"[USER]: {transcript}"
            )

            conn.execute(
                """
                UPDATE voice_calls SET 
                    transcript = ?,
                    intent_detected = ?,
                    sentiment_score = ?,
                    disposition = ?,
                    status = ?
                WHERE id = ?
                """,
                (
                    new_transcript,
                    intent.value,
                    sentiment,
                    disposition,
                    CallStatus.IN_PROGRESS.value,
                    call_id,
                ),
            )
            conn.commit()

    async def get_call_status(self, call_id: str) -> Optional[VoiceCall]:
        """Get current status of a voice call"""
        with self.engine.connect() as conn:
            result = conn.execute(
                "SELECT * FROM voice_calls WHERE id = ?", (call_id,)
            ).fetchone()

            if result:
                return VoiceCall(
                    id=result[0],
                    lead_id=result[1],
                    phone_number=result[2],
                    status=CallStatus(result[3]),
                    persona=LeadPersona(result[4]),
                    intent_detected=IntentType(result[5]) if result[5] else None,
                    transcript=result[6],
                    sentiment_score=result[7],
                    disposition=result[8],
                    callback_scheduled=datetime.fromisoformat(result[9])
                    if result[9]
                    else None,
                    created_at=datetime.fromisoformat(result[10]),
                    completed_at=datetime.fromisoformat(result[11])
                    if result[11]
                    else None,
                    duration_seconds=result[12],
                    retell_call_id=result[13],
                )
        return None

    async def batch_initiate_campaign(
        self, leads: List[Dict], campaign_type: str = "initial_outbound"
    ) -> List[VoiceCall]:
        """Initiate voice campaign for multiple leads"""
        calls = []

        for lead in leads:
            try:
                persona = LeadPersona(lead.get("persona", "realist"))
                call = await self.initiate_outbound_call(
                    lead_id=lead["id"],
                    phone_number=lead["phone"],
                    campaign_type=campaign_type,
                    persona=persona,
                )
                calls.append(call)

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to initiate call for lead {lead['id']}: {e}")
                continue

        return calls

    def get_campaign_analytics(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> Dict:
        """Get analytics for voice campaign performance"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        with self.engine.connect() as conn:
            stats = conn.execute(
                """
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(duration_seconds) as avg_duration,
                    disposition,
                    persona
                FROM voice_calls 
                WHERE created_at BETWEEN ? AND ?
                GROUP BY status, disposition, persona
                """,
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()

            total_calls = sum(row[1] for row in stats)
            completed_calls = sum(row[1] for row in stats if row[0] == "completed")
            qualified_leads = sum(
                row[1] for row in stats if row[3] in ["QUALIFIED_HOT", "SCHEDULED"]
            )

            return {
                "total_calls": total_calls,
                "completed_calls": completed_calls,
                "completion_rate": completed_calls / total_calls
                if total_calls > 0
                else 0,
                "qualified_leads": qualified_leads,
                "qualification_rate": qualified_leads / completed_calls
                if completed_calls > 0
                else 0,
                "by_status": {row[0]: row[1] for row in stats},
                "by_disposition": {row[3]: row[1] for row in stats},
                "by_persona": {row[4].value: row[1] for row in stats},
            }


class InsuranceNavigatorService:
    """AI-powered insurance claims navigation"""

    def __init__(self, voice_service: RetellVoiceService):
        self.voice_service = voice_service
        self.claim_process_stages = [
            "initial_report",
            "adjuster_meeting",
            "estimate_preparation",
            "claim_submission",
            "negotiation",
            "approval",
            "repair_scheduling",
            "completion",
        ]

    async def initiate_claim_assistance_call(
        self, lead_id: str, phone_number: str, claim_number: str = None
    ) -> VoiceCall:
        """Initiate insurance claim assistance call"""
        return await self.voice_service.initiate_outbound_call(
            lead_id=lead_id,
            phone_number=phone_number,
            campaign_type="insurance_claim",
            persona=LeadPersona.URGENT,
        )

    def get_claim_navigation_script(self, claim_stage: str) -> str:
        """Get script for specific claim stage"""
        scripts = {
            "initial_report": """Hello! I'm helping you navigate your insurance claim for storm damage. 
First, I need to gather some information about the damage. Can you describe what you found?""",
            "adjuster_meeting": """I'll help you prepare for your adjuster meeting. 
Here are key points to discuss: 1) Document all damage with photos, 2) Get the adjuster's estimate in writing, 
3) Ask about replacement cost vs. actual cash value.""",
            "estimate_preparation": """Let's prepare your estimate. I'll need: 1) Roof square footage, 
2) Number of layers being removed, 3) Type of roofing material, 4) Any additional features like skylights or vents.""",
            "claim_submission": """I'll help you submit your claim properly. Make sure to include: 
All photos, detailed written description, any contractor estimates, and reference your policy coverage.""",
            "negotiation": """If your claim is underpaid, we can appeal. Key negotiation points: 
Replacement cost coverage, code upgrades, hidden damage discovery, and depreciation calculations.""",
            "approval": """Congratulations on your claim approval! Let's review the final scope and 
schedule your repair work. Do you have a preferred start date?""",
            "repair_scheduling": """I'll coordinate your repair schedule. Typical timeline is 1-2 weeks 
from approval. We'll need 2-3 days of good weather for the installation.""",
            "completion": """Your roof repair is complete! Let's do a final walkthrough together 
to ensure everything meets your expectations. Would you like to schedule this?""",
        }

        return scripts.get(claim_stage, scripts["initial_report"])

    async def process_claim_intake(self, lead_id: str, transcript: str) -> Dict:
        """Process insurance claim intake from voice transcript"""
        intent = self.voice_service._detect_intent(transcript)

        claim_info = {
            "claim_stage": "initial_report",
            "follow_up_required": True,
            "documents_needed": [],
            "next_action": "schedule_adjuster_meeting",
        }

        if intent == IntentType.INSURANCE_CLAIM:
            claim_info["claim_stage"] = "initial_report"
            claim_info["documents_needed"] = [
                "policy_number",
                "damage_photos",
                "initial_estimate",
            ]

        return claim_info


class StormResponseVoiceAutomation:
    """Automated voice response triggered by storm events"""

    def __init__(self, voice_service: RetellVoiceService):
        self.voice_service = voice_service
        self.storm_thresholds = {
            "hail_size_inches": 1.5,
            "wind_speed_mph": 60,
            "damage_probability": 0.75,
        }

    async def trigger_storm_campaign(
        self, storm_event: Dict, affected_leads: List[Dict]
    ) -> Dict:
        """Trigger voice campaign for storm-affected leads"""
        storm_type = storm_event.get("type", "hail")
        urgency_level = self._calculate_urgency(storm_event)

        campaign_type = (
            "leak_emergency" if urgency_level == "critical" else "initial_outbound"
        )

        results = {
            "storm_event": storm_event["id"],
            "campaign_type": campaign_type,
            "leads_contacted": 0,
            "calls_initiated": [],
            "qualified_leads": 0,
            "estimated_reach": len(affected_leads),
        }

        for lead in affected_leads:
            try:
                call = await self.voice_service.initiate_outbound_call(
                    lead_id=lead["id"],
                    phone_number=lead["phone"],
                    campaign_type=campaign_type,
                    persona=self._get_persona_for_storm(lead, urgency_level),
                )
                results["calls_initiated"].append(call.id)
                results["leads_contacted"] += 1

                if call.status in [CallStatus.INITIATED, CallStatus.IN_PROGRESS]:
                    results["qualified_leads"] += 1

            except Exception as e:
                logger.error(f"Failed to call lead {lead['id']}: {e}")
                continue

        return results

    def _calculate_urgency(self, storm_event: Dict) -> str:
        """Calculate urgency level based on storm severity"""
        hail_size = storm_event.get("hail_size_inches", 0)
        wind_speed = storm_event.get("wind_speed_mph", 0)
        damage_prob = storm_event.get("damage_probability", 0)

        if hail_size >= 2.0 or wind_speed >= 75 or damage_prob >= 0.9:
            return "critical"
        elif hail_size >= 1.5 or wind_speed >= 60 or damage_prob >= 0.75:
            return "high"
        else:
            return "normal"

    def _get_persona_for_storm(self, lead: Dict, urgency: str) -> LeadPersona:
        """Determine best persona for lead based on storm context"""
        if urgency == "critical":
            return LeadPersona.URGENT

        lead_history = lead.get("history", {})
        if lead_history.get("previous_claims"):
            return LeadPersona.QUALITY
        elif lead_history.get("financing_inquiries"):
            return LeadPersona.SKEPTIC
        else:
            return LeadPersona.REALIST


class VoiceComplianceLayer:
    """Compliance monitoring for voice operations"""

    def __init__(self):
        self.compliance_rules = {
            "tcpa_compliant": True,
            "calling_hours": (8, 21),
            "do_not_call_check": True,
            "opt_out_handling": True,
            "recording_disclosure": True,
        }

    def validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        pattern = r"^\+?1?\d{9,14}$"
        return bool(re.match(pattern, phone))

    def check_calling_hours(self, phone: str = None) -> bool:
        """Check if current time is within allowed calling hours"""
        current_hour = datetime.utcnow().hour
        start, end = self.compliance_rules["calling_hours"]
        return start <= current_hour <= end

    def should_call(self, phone: str, lead_record: Dict) -> tuple[bool, str]:
        """Determine if call should proceed based on compliance rules"""
        if not self.validate_phone_number(phone):
            return False, "Invalid phone number"

        if not self.check_calling_hours():
            return False, "Outside calling hours (8 AM - 9 PM local time)"

        if lead_record.get("do_not_call"):
            return False, "Lead is on do-not-call list"

        if lead_record.get("opted_out"):
            return False, "Lead has opted out of communications"

        if lead_record.get("last_contact") and (
            datetime.fromisoformat(lead_record["last_contact"])
            > datetime.utcnow() - timedelta(hours=24)
        ):
            return False, "Contact frequency restriction (24-hour cooldown)"

        return True, "Call approved"

    def get_tcpa_disclosure(self) -> str:
        """Get TCPA compliance disclosure script"""
        return """This call may be monitored or recorded for quality assurance purposes. 
By continuing, you consent to receive calls regarding our roofing services at this number. 
Reply STOP to opt out of future communications."""

    def get_opt_out_response(self) -> str:
        """Get opt-out acknowledgment response"""
        return """Thank you for your feedback. I've removed your number from our active calling list. 
You will not receive further calls from StormOps Roofing. Is there anything else I can help you with today?"""


def create_voice_service(
    api_key: str, database_url: str = "sqlite:///stormops.db"
) -> RetellVoiceService:
    """Factory function to create voice service instance"""
    engine = create_engine(database_url)
    return RetellVoiceService(api_key=api_key, engine=engine)


if __name__ == "__main__":
    import os

    API_KEY = os.getenv("RETELL_API_KEY")

    if not API_KEY:
        logger.error("RETELL_API_KEY environment variable not set")
        exit(1)

    service = create_voice_service(API_KEY)

    async def test():
        call = await service.initiate_outbound_call(
            lead_id="TEST-001",
            phone_number="+15551234567",
            campaign_type="initial_outbound",
            persona=LeadPersona.REALIST,
        )
        print(f"Call initiated: {call.id}")

        analytics = service.get_campaign_analytics()
        print(f"Campaign analytics: {json.dumps(analytics, indent=2)}")

    asyncio.run(test())
