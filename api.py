"""
FastAPI layer exposing Storm Lead Finder endpoints.
Reuses existing Python modules: dfw_hotspots, roofing_ai, causal_impact, etc.
"""

import os
import json
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(__file__)

# --- Pydantic Models ---


class ZipMetricsResponse(BaseModel):
    zip_code: str
    storm_score: float
    risk_level: str
    wind_max: float
    lead_pot_hours: float
    earliest_safe_start: int
    best_playbook: str
    playbook_lift: int


class MapDataResponse(BaseModel):
    storm_id: str
    timestamp: str
    zip_codes: List[Dict[str, Any]]


class TimelineResponse(BaseModel):
    storm_id: str
    peak_hour_utc: int
    hours_at_high_risk: int
    earliest_safe_start_by_job: Dict[str, int]
    job_buffers: Dict[str, Dict[str, int]]


class AIAssistantRequest(BaseModel):
    prompt: str
    context: Dict[str, Any]


class AIAssistantResponse(BaseModel):
    answer: str


class CausalImpactResponse(BaseModel):
    storm_id: str
    incremental_inspections: int
    incremental_jobs: int
    incremental_revenue: float
    playbook_lifts: List[Dict[str, Any]]


# --- Voice API Models ---


class InitiateCallRequest(BaseModel):
    lead_id: str
    phone_number: str
    campaign_type: str = "initial_outbound"
    persona: str = "realist"


class VoiceCallResponse(BaseModel):
    call_id: str
    lead_id: str
    status: str
    persona: str
    intent_detected: Optional[str] = None
    disposition: Optional[str] = None
    created_at: str


class VoiceCampaignRequest(BaseModel):
    lead_ids: List[str]
    campaign_type: str = "initial_outbound"
    persona: str = "realist"


class VoiceCampaignResponse(BaseModel):
    campaign_id: str
    calls_initiated: int
    status: str
    message: str


class ProcessVoiceInputRequest(BaseModel):
    call_id: str
    transcript: str


class ProcessVoiceInputResponse(BaseModel):
    intent: str
    sentiment_score: float
    disposition: str
    recommended_action: str


class VoiceAnalyticsResponse(BaseModel):
    total_calls: int
    completed_calls: int
    completion_rate: float
    qualified_leads: int
    qualification_rate: float
    by_status: Dict[str, int]
    by_disposition: Dict[str, int]
    by_persona: Dict[str, int]


class StormVoiceTriggerRequest(BaseModel):
    storm_event_id: str
    storm_type: str = "hail"
    urgency_level: str = "normal"
    affected_lead_ids: List[str]


# --- Load Data Helpers ---


def load_storm_data():
    """Load storm data from existing outputs."""
    areas_csv = os.path.join(BASE_DIR, "outputs", "dfw_hotspots_areas.csv")
    if not os.path.exists(areas_csv):
        return None

    import pandas as pd

    df = pd.read_csv(areas_csv)
    return df


def load_roof_risk_index():
    """Load Roof Risk Index from database."""
    rri_db = os.path.join(BASE_DIR, "outputs", "roof_risk_index.db")
    if not os.path.exists(rri_db):
        return {}

    import sqlite3

    try:
        conn = sqlite3.connect(rri_db)
        rri_df = pd.read_sql_query("SELECT zip, risk_score FROM zip_risk", conn)
        conn.close()
        return dict(zip(rri_df["zip"], rri_df["risk_score"]))
    except Exception:
        return {}


# --- Job Type Config ---
JOB_TYPES = {
    "Tear-off / Demo": {"buffer_hours": 48, "wind_limit": 15, "duration_hours": 8},
    "Membrane Install": {"buffer_hours": 24, "wind_limit": 20, "duration_hours": 6},
    "Inspection / Canvassing": {
        "buffer_hours": 6,
        "wind_limit": 25,
        "duration_hours": 0.5,
    },
}


def get_best_playbook(risk_level: str, job_type: str) -> Dict[str, Any]:
    """Return best playbook based on risk."""
    if risk_level == "High":
        return {
            "name": "Door + SMS",
            "lift": 18,
            "description": "Immediate follow-up with SMS",
        }
    elif risk_level == "Medium":
        return {
            "name": "Door + Flyer",
            "lift": 12,
            "description": "Leave detailed flyer",
        }
    else:
        return {
            "name": "Direct Mail",
            "lift": 5,
            "description": "Cost-effective bulk mailer",
        }


# --- FastAPI App ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load data once
    app.state.df = load_storm_data()
    app.state.rri = load_roof_risk_index()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Storm Lead Finder API",
    description="Backend API for Storm Lead Finder - roofing storm intelligence",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---


@app.get("/")
def root():
    return {"name": "Storm Lead Finder API", "status": "healthy", "version": "1.0.0"}


@app.get("/storms/{storm_id}/zip-metrics", response_model=List[ZipMetricsResponse])
def get_zip_metrics(storm_id: str, job_type: str = "Tear-off / Demo"):
    """Get top ZIP metrics for a storm, filtered by job type."""
    df = app.state.df
    if df is None:
        raise HTTPException(status_code=404, detail="Storm data not found")

    config = JOB_TYPES.get(job_type, JOB_TYPES["Tear-off / Demo"])
    results = []

    for _, row in df.iterrows():
        zip_code = str(row.get("ZCTA5CE10", row.get("ZIP", "")))
        if not zip_code:
            continue

        risk = row.get("damage_risk", "Low")
        lead_pot = (row.get("n_cells", 1) * 100) * config["duration_hours"]
        safe_start = int(row.get("peak_hour_idx_mode", 0)) + config["buffer_hours"]
        playbook = get_best_playbook(risk, job_type)

        results.append(
            ZipMetricsResponse(
                zip_code=zip_code,
                storm_score=float(row.get("storm_score_max", 0)),
                risk_level=risk,
                wind_max=float(row.get("max_wind_max", 0)),
                lead_pot_hours=lead_pot,
                earliest_safe_start=safe_start,
                best_playbook=playbook["name"],
                playbook_lift=playbook["lift"],
            )
        )

    # Sort by storm score descending
    results.sort(key=lambda x: x.storm_score, reverse=True)
    return results[:20]


@app.get("/storms/{storm_id}/map-data", response_model=MapDataResponse)
def get_map_data(storm_id: str, layer: str = "ZIP"):
    """Get map data for rendering in React frontend."""
    df = app.state.df
    if df is None:
        raise HTTPException(status_code=404, detail="Storm data not found")

    zip_codes = []
    for _, row in df.iterrows():
        zip_code = str(row.get("ZCTA5CE10", row.get("ZIP", "")))
        if zip_code:
            zip_codes.append(
                {
                    "zip": zip_code,
                    "score": float(row.get("storm_score_max", 0)),
                    "risk": row.get("damage_risk", "Low"),
                    "wind": float(row.get("max_wind_max", 0)),
                    "cells": int(row.get("n_cells", 1)),
                }
            )

    return MapDataResponse(
        storm_id=storm_id,
        timestamp=datetime.now().isoformat(),
        zip_codes=zip_codes,
    )


@app.get("/storms/{storm_id}/timeline", response_model=TimelineResponse)
def get_timeline(storm_id: str):
    """Get timeline data for a storm."""
    df = app.state.df
    if df is None:
        raise HTTPException(status_code=404, detail="Storm data not found")

    first_row = df.iloc[0] if len(df) > 0 else {}

    peak_hour = int(first_row.get("peak_hour_idx_mode", 0))
    hours_risk = int(first_row.get("hours_high_risk_max", 0))

    # Calculate safe start for each job type
    earliest_safe_start = {}
    buffers = {}
    for job, config in JOB_TYPES.items():
        safe_start = peak_hour + config["buffer_hours"]
        earliest_safe_start[job] = safe_start
        buffers[job] = {
            "buffer_hours": config["buffer_hours"],
            "wind_limit": config["wind_limit"],
        }

    return TimelineResponse(
        storm_id=storm_id,
        peak_hour_utc=peak_hour,
        hours_at_high_risk=hours_risk,
        earliest_safe_start_by_job=earliest_safe_start,
        job_buffers=buffers,
    )


@app.post("/ai/assistant", response_model=AIAssistantResponse)
def ai_assistant(request: AIAssistantRequest):
    """AI assistant endpoint wrapping roofing_ai.py logic."""
    try:
        from roofing_ai import RoofingAIAssistant

        assistant = RoofingAIAssistant()

        # Build context from request
        context = request.context
        view = context.get("view", "unknown")
        job_type = context.get("job_type", "")

        assistant.context = {
            "storm": context.get("storm", {}),
            "zip": context.get("zip", {}),
            "job": context.get("job", {}),
        }

        # Generate response using fallback system
        answer = assistant._fallback_response(request.prompt)

        return AIAssistantResponse(answer=answer)
    except Exception as e:
        return AIAssistantResponse(answer=f"Error: {str(e)}")


@app.get("/storms/{storm_id}/causal-impact", response_model=CausalImpactResponse)
def get_causal_impact(storm_id: str):
    """Get causal impact metrics for a storm."""
    df = app.state.df
    if df is None:
        raise HTTPException(status_code=404, detail="Storm data not found")

    # Calculate incremental metrics (mocked - would come from causal_impact.py)
    avg_score = df["storm_score_max"].mean() if len(df) > 0 else 0
    zip_count = len(df)

    # Estimate impact based on storm severity
    inspection_lift = int(avg_score * 500)
    job_lift = int(avg_score * 200)
    revenue_lift = job_lift * 8000  # ~$8k per job

    playbook_lifts = [
        {
            "playbook": "Door + SMS",
            "lift": 18,
            "description": "Highest conversion for high-risk areas",
        },
        {"playbook": "Door + Flyer", "lift": 12, "description": "Good for medium-risk"},
        {
            "playbook": "Direct Mail",
            "lift": 5,
            "description": "Cost-effective for low-touch",
        },
    ]

    return CausalImpactResponse(
        storm_id=storm_id,
        incremental_inspections=inspection_lift,
        incremental_jobs=job_lift,
        incremental_revenue=revenue_lift,
        playbook_lifts=playbook_lifts,
    )


class LeadsResponse(BaseModel):
    id: str
    name: str
    phone: str
    persona: str
    storm_risk_score: float
    last_contact: Optional[str] = None


@app.get("/leads")
def get_leads(voice_ready: bool = False):
    """Get all leads from the database."""
    try:
        conn = sqlite3.connect("stormops_cache.db")
        cursor = conn.cursor()

        query = "SELECT lead_id, phone, persona, lead_score, last_contact, address FROM leads"

        if voice_ready:
            query += " WHERE voice_ready = 1"

        query += " ORDER BY lead_score DESC LIMIT 100"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        leads = []
        for row in rows:
            leads.append(
                {
                    "id": row[0],
                    "name": row[5] if row[5] else f"Lead {row[0]}",
                    "phone": row[1] or "",
                    "persona": row[2] or "realist",
                    "storm_risk_score": (row[3] / 100) if row[3] else 0,
                    "last_contact": row[4],
                }
            )

        return leads
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads/{lead_id}")
def get_lead_detail(lead_id: str):
    """Get detailed information for a specific lead."""
    conn = sqlite3.connect("stormops_cache.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM leads WHERE lead_id = ?
    """,
        (lead_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")

    columns = [desc[0] for desc in cursor.description]

    return dict(zip(columns, row))


@app.post("/leads/{lead_id}/voice-campaign")
def add_to_voice_campaign(lead_id: str):
    """Add a lead to the voice campaign queue."""
    conn = sqlite3.connect("stormops_cache.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE leads SET voice_ready = 1 WHERE lead_id = ?", (lead_id,))
    conn.commit()
    conn.close()

    return {"status": "success", "lead_id": lead_id, "voice_ready": True}


# --- Voice API Endpoints ---


@app.post("/voice/initiate-call", response_model=VoiceCallResponse)
def initiate_voice_call(
    request: InitiateCallRequest, background_tasks: BackgroundTasks
):
    """Initiate an outbound voice call to a lead."""
    from services.voice_service import RetellVoiceService, LeadPersona, CallStatus

    api_key = os.getenv("RETELL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RETELL_API_KEY not configured")

    try:
        voice_service = RetellVoiceService(api_key=api_key)

        persona = LeadPersona(request.persona)

        call = asyncio.run(
            voice_service.initiate_outbound_call(
                lead_id=request.lead_id,
                phone_number=request.phone_number,
                campaign_type=request.campaign_type,
                persona=persona,
            )
        )

        return VoiceCallResponse(
            call_id=call.id,
            lead_id=call.lead_id,
            status=call.status.value,
            persona=call.persona.value,
            intent_detected=call.intent_detected.value
            if call.intent_detected
            else None,
            disposition=call.disposition,
            created_at=call.created_at.isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate call: {str(e)}"
        )


@app.post("/voice/campaign", response_model=VoiceCampaignResponse)
def initiate_voice_campaign(
    request: VoiceCampaignRequest, background_tasks: BackgroundTasks
):
    """Initiate a voice campaign for multiple leads."""
    from services.voice_service import RetellVoiceService, LeadPersona

    api_key = os.getenv("RETELL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RETELL_API_KEY not configured")

    try:
        voice_service = RetellVoiceService(api_key=api_key)

        persona = LeadPersona(request.persona)

        leads = [{"id": lid, "phone": ""} for lid in request.lead_ids]

        campaign_id = f"CAMP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        asyncio.run(
            voice_service.batch_initiate_campaign(
                leads=leads, campaign_type=request.campaign_type
            )
        )

        return VoiceCampaignResponse(
            campaign_id=campaign_id,
            calls_initiated=len(leads),
            status="initiated",
            message=f"Campaign {campaign_id} initiated for {len(leads)} leads",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate campaign: {str(e)}"
        )


@app.post("/voice/process-input", response_model=ProcessVoiceInputResponse)
def process_voice_input(request: ProcessVoiceInputRequest):
    """Process voice input from a call."""
    from services.voice_service import RetellVoiceService

    api_key = os.getenv("RETELL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RETELL_API_KEY not configured")

    try:
        voice_service = RetellVoiceService(api_key=api_key)

        result = voice_service._detect_intent(request.transcript)
        sentiment = voice_service._analyze_sentiment(request.transcript)
        disposition = voice_service._determine_disposition(result, sentiment)
        recommended_action = voice_service._get_recommended_action(result, sentiment)

        return ProcessVoiceInputResponse(
            intent=result.value,
            sentiment_score=sentiment,
            disposition=disposition,
            recommended_action=recommended_action,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process input: {str(e)}"
        )


@app.get("/voice/call/{call_id}", response_model=VoiceCallResponse)
def get_call_status(call_id: str):
    """Get the status of a voice call."""
    from services.voice_service import RetellVoiceService

    api_key = os.getenv("RETELL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RETELL_API_KEY not configured")

    try:
        voice_service = RetellVoiceService(api_key=api_key)

        call = asyncio.run(voice_service.get_call_status(call_id))

        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        return VoiceCallResponse(
            call_id=call.id,
            lead_id=call.lead_id,
            status=call.status.value,
            persona=call.persona.value,
            intent_detected=call.intent_detected.value
            if call.intent_detected
            else None,
            disposition=call.disposition,
            created_at=call.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get call status: {str(e)}"
        )


@app.get("/voice/analytics", response_model=VoiceAnalyticsResponse)
def get_voice_analytics(
    start_date: Optional[str] = None, end_date: Optional[str] = None
):
    """Get voice campaign analytics."""
    from services.voice_service import RetellVoiceService

    api_key = os.getenv("RETELL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RETELL_API_KEY not configured")

    try:
        voice_service = RetellVoiceService(api_key=api_key)

        start = (
            datetime.fromisoformat(start_date)
            if start_date
            else datetime.utcnow() - timedelta(days=30)
        )
        end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()

        analytics = voice_service.get_campaign_analytics(start_date=start, end_date=end)

        return VoiceAnalyticsResponse(
            total_calls=analytics["total_calls"],
            completed_calls=analytics["completed_calls"],
            completion_rate=analytics["completion_rate"],
            qualified_leads=analytics["qualified_leads"],
            qualification_rate=analytics["qualification_rate"],
            by_status=analytics["by_status"],
            by_disposition=analytics["by_disposition"],
            by_persona=analytics["by_persona"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get analytics: {str(e)}"
        )


@app.post("/voice/storm-trigger")
def trigger_storm_voice_campaign(
    request: StormVoiceTriggerRequest, background_tasks: BackgroundTasks
):
    """Trigger voice campaign for storm-affected leads."""
    from services.voice_service import (
        RetellVoiceService,
        StormResponseVoiceAutomation,
        LeadPersona,
    )

    api_key = os.getenv("RETELL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RETELL_API_KEY not configured")

    try:
        voice_service = RetellVoiceService(api_key=api_key)
        storm_automation = StormResponseVoiceAutomation(voice_service)

        storm_event = {
            "id": request.storm_event_id,
            "type": request.storm_type,
            "urgency": request.urgency_level,
        }

        leads = [{"id": lid, "phone": ""} for lid in request.affected_lead_ids]

        results = asyncio.run(
            storm_automation.trigger_storm_campaign(storm_event, leads)
        )

        return {
            "status": "campaign_initiated",
            "storm_event_id": request.storm_event_id,
            "leads_targeted": len(leads),
            "results": results,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger storm campaign: {str(e)}"
        )


@app.post("/voice/insurance-navigator")
def initiate_insurance_navigator_call(
    lead_id: str, phone_number: str, claim_number: str = None
):
    """Initiate insurance claim navigation call."""
    from services.voice_service import RetellVoiceService, InsuranceNavigatorService

    api_key = os.getenv("RETELL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RETELL_API_KEY not configured")

    try:
        voice_service = RetellVoiceService(api_key=api_key)
        navigator = InsuranceNavigatorService(voice_service)

        call = asyncio.run(
            navigator.initiate_claim_assistance_call(
                lead_id=lead_id, phone_number=phone_number, claim_number=claim_number
            )
        )

        return {
            "status": "call_initiated",
            "call_id": call.id,
            "lead_id": lead_id,
            "claim_number": claim_number,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate insurance navigator: {str(e)}"
        )


# --- Run with: uvicorn api:app --reload ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
