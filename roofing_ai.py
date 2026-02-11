import os
from typing import Dict, Any, Optional
from state import AppState
from sidebar_state import SidebarState, ActionButton, ConnectionNode, ScoreBreakdown
from datetime import datetime
from services.earth2_service import Earth2Service
from services.property_service import PropertyService
from services.lead_scoring_service import LeadScoringService
from services.routing_service import RoutingService
from services.crm_service import CRMService

# Import thresholds from app
MISSION_THRESHOLDS = {
    "detect_storm": {"hot_zones": 5, "update_hours": 2},
    "map_targets": {"doors": 1000, "hot_zips": 3},
    "build_routes": {"routes": 2, "value": 50000},
    "job_intel": {"inspected": 5, "claims": 2},
    "nurture_loop": {"reviews": 3, "followups": 5},
}


class RoofingAIAssistant:
    """
    AI assistant wrapper for StormOps that provides roofing-specific responses.
    Now state-aware and can manipulate the sidebar control plane.
    """

    def __init__(self, opencode_url: str = "http://localhost:11434"):
        self.base_url = opencode_url
        self.model = "llama3.2"
        self.context: Dict[str, Any] = {}

    def set_context(self, context_type: str, data: Dict):
        self.context[context_type] = data

    def build_sidebar_state(self, app_state: AppState) -> SidebarState:
        """Build complete sidebar state from app state."""
        step = app_state.mission.current_step
        step_code = ["01", "02", "03", "04", "05"][
            [
                "detect_storm",
                "map_targets",
                "build_routes",
                "job_intel",
                "nurture_loop",
            ].index(step)
        ]

        sidebar = SidebarState(current_phase=step, phase_code=step_code)

        # Initialize actions
        sidebar.actions = {
            "load_storm": ActionButton(
                "load_storm", "Load Storm Data", enabled=step == "detect_storm"
            ),
            "select_zones": ActionButton(
                "select_zones", "Select Target Zones", enabled=step == "map_targets"
            ),
            "build_routes": ActionButton(
                "build_routes", "Build Routes", enabled=step == "build_routes"
            ),
            "draft_sms": ActionButton("draft_sms", "Draft Outreach", enabled=True),
        }

        # Initialize connections
        sidebar.connections = {
            "earth2": ConnectionNode("EARTH-2", "online", datetime.now()),
            "attom": ConnectionNode("ATTOM", "online", datetime.now()),
            "jobnimbus": ConnectionNode("JOBNIMBUS", "online", datetime.now()),
        }

        # Calculate score breakdown
        sidebar.score = self._calculate_score_breakdown(app_state)

        return sidebar

    def _calculate_score_breakdown(self, app_state: AppState) -> ScoreBreakdown:
        """Calculate detailed score with gap analysis."""
        doors = app_state.stats.get("doors_targeted", 0)
        routes = app_state.routes_created
        claims = app_state.stats.get("claims_filed", 0)

        detection = min(20, (len(app_state.zones) / 10) * 20) if app_state.zones else 0
        targeting = min(30, (doors / 1000) * 30)
        routing = min(25, (routes / 2) * 25)
        intel = min(15, (claims / 2) * 15)
        nurture = 0  # Not implemented yet

        total = int(detection + targeting + routing + intel + nurture)

        # Gap analysis
        gaps = []
        if doors < 1000:
            gaps.append(
                {
                    "action_id": "select_zones",
                    "impact": 30 - targeting,
                    "message": f"Need {1000 - doors:,} more doors",
                }
            )
        if routes < 2:
            gaps.append(
                {
                    "action_id": "build_routes",
                    "impact": 25 - routing,
                    "message": f"Need {2 - routes} more routes",
                }
            )
        if claims < 2:
            gaps.append(
                {
                    "action_id": "file_claims",
                    "impact": 15 - intel,
                    "message": f"Need {2 - claims} more claims",
                }
            )

        return ScoreBreakdown(
            total,
            int(detection),
            int(targeting),
            int(routing),
            int(intel),
            int(nurture),
            gaps,
        )

    def set_context(self, context_type: str, data: Dict):
        self.context[context_type] = data

    def generate_response(
        self, user_question: str, app_state: AppState
    ) -> Dict[str, Any]:
        """
        Generate AI response that EXECUTES actions and manipulates sidebar state.
        Returns: {text, actions, sidebar_updates, confidence}
        """
        q_lower = user_question.lower()
        step = app_state.mission.current_step

        # Build sidebar state
        sidebar = self.build_sidebar_state(app_state)

        # INTENT: What should I do next? (Proactive AI)
        if any(
            word in q_lower
            for word in ["what next", "what should", "recommend", "suggest"]
        ):
            next_action_id = sidebar.get_next_best_action()
            if next_action_id and next_action_id in sidebar.actions:
                action = sidebar.actions[next_action_id]
                gap = next(
                    g for g in sidebar.score.gaps if g["action_id"] == next_action_id
                )

                # Propose the action (ghost state)
                sidebar.propose_action(next_action_id)

                return {
                    "text": f"**Next Best Action:** {action.label}\n\n{gap['message']}\n\nThis will add +{gap['impact']:.0f} points to your score.\n\nClick the highlighted button or say 'Execute {action.label}'",
                    "actions": ["propose", next_action_id],
                    "sidebar_updates": sidebar.to_dict(),
                    "confidence": 0.95,
                }

        # INTENT: Which ZIPs to target?
        if any(
            word in q_lower
            for word in ["which zip", "where should", "target first", "prioritize"]
        ):
            if not app_state.zones:
                sidebar.execute_action("load_storm")
                return {
                    "text": "No storm data loaded. Loading DFW Storm-24 now...",
                    "actions": ["load_storm_event"],
                    "sidebar_updates": sidebar.to_dict(),
                    "confidence": 0.95,
                }

            # Rank zones by impact
            top_zones = sorted(
                app_state.zones.values(), key=lambda x: x.impact_index, reverse=True
            )[:3]
            zone_list = "\n".join(
                [
                    f"• {z.zip_code} - {z.estimated_roofs:,} roofs, ${z.lead_value / 1e6:.1f}M potential"
                    for z in top_zones
                ]
            )

            sidebar.execute_action("select_zones")

            return {
                "text": f"**Top 3 ZIPs for Storm DFW-24:**\n\n{zone_list}\n\nPre-selecting these zones on the map now.",
                "actions": [
                    "select_zones",
                    top_zones[0].zip_code,
                    top_zones[1].zip_code,
                    top_zones[2].zip_code,
                ],
                "sidebar_updates": sidebar.to_dict(),
                "next_step": "map_targets",
                "confidence": 0.98,
            }

        # INTENT: Build routes
        if any(
            word in q_lower
            for word in ["build route", "optimize route", "crew route", "canvass"]
        ):
            selected_zones = [z for z in app_state.zones.values() if z.selected]
            if not selected_zones:
                return {
                    "text": "No zones selected. Select at least 3 HOT ZIPs first.",
                    "actions": [],
                    "sidebar_updates": sidebar.to_dict(),
                    "confidence": 0.9,
                }

            total_doors = sum(z.estimated_roofs for z in selected_zones)
            sidebar.execute_action("build_routes")

            return {
                "text": f"**Building routes for {len(selected_zones)} zones ({total_doors:,} doors)**\n\nGenerating 2 optimized routes with proximity clustering.",
                "actions": ["build_routes", "auto"],
                "sidebar_updates": sidebar.to_dict(),
                "next_step": "build_routes",
                "confidence": 0.97,
            }

        # INTENT: Draft outreach
        if any(
            word in q_lower
            for word in ["draft", "sms", "message", "script", "outreach"]
        ):
            sidebar.execute_action("draft_sms")
            return {
                "text": "**Insurance Help SMS (Urgent/Safety tone):**\n\n'Hi [Name], this is [Your Company]. We noticed your area was hit by 2.5\" hail on [Date]. Many roofs in [ZIP] sustained damage. We offer FREE inspections and work directly with your insurance. No out-of-pocket cost. Reply YES for a quick check.'\n\nCopy to clipboard?",
                "actions": ["show_script", "insurance_sms"],
                "sidebar_updates": sidebar.to_dict(),
                "confidence": 0.96,
            }

        # INTENT: Show metrics / status
        if any(word in q_lower for word in ["status", "progress", "how many", "score"]):
            score_data = sidebar.score
            status = "On track" if score_data.total > 50 else "Need more doors/routes"

            gaps_text = "\n".join([f"• {g['message']}" for g in score_data.gaps[:3]])

            return {
                "text": f"**Storm Play Status:**\n\n• Score: {score_data.total}/100\n• Detection: {score_data.detection}/20\n• Targeting: {score_data.targeting}/30\n• Routing: {score_data.routing}/25\n\n**Gaps:**\n{gaps_text}\n\n{status}",
                "actions": [],
                "sidebar_updates": sidebar.to_dict(),
                "confidence": 0.99,
            }

        # INTENT: Generate leads
        if any(
            word in q_lower for word in ["generate lead", "find lead", "create lead"]
        ):
            return {
                "text": "**Generating leads from Earth-2 storm data...**\n\nAnalyzing affected ZIPs and property data.",
                "actions": ["generate_leads"],
                "sidebar_updates": sidebar.to_dict()
                if hasattr(self, "build_sidebar_state")
                else {},
                "confidence": 0.96,
            }

        # INTENT: Predict weather
        if any(
            word in q_lower for word in ["predict", "forecast", "weather", "markov"]
        ):
            return {
                "text": "**Running Markov chain weather prediction...**\n\nAnalyzing 7-day forecast with optimal canvassing windows.",
                "actions": ["predict_weather"],
                "sidebar_updates": sidebar.to_dict()
                if hasattr(self, "build_sidebar_state")
                else {},
                "confidence": 0.94,
            }

        # Fallback: Be helpful
        return {
            "text": "I can help you:\n\n• 'Generate leads' - Create qualified leads from Earth-2 data\n• 'Which ZIPs to target?' - Analyze & select zones\n• 'Build routes' - Generate optimized paths\n• 'Predict weather' - Run 7-day Markov forecast\n• 'What should I do next?' - Get AI guidance\n\nWhat would you like to do?",
            "actions": [],
            "sidebar_updates": sidebar.to_dict()
            if hasattr(self, "build_sidebar_state")
            else {},
            "confidence": 0.7,
        }

    def _get_next_action(self, app_state: AppState) -> Dict[str, Any]:
        """Intelligent next-action recommendation based on current state."""
        step = app_state.mission.current_step
        score = app_state.mission.play_score

        if step == "detect_storm":
            if not app_state.zones:
                return {
                    "text": "**Next:** Load Storm DFW-24 to identify hot zones.\n\nClick 'Load event & find targets'",
                    "actions": ["highlight_button", "load_event"],
                    "confidence": 0.95,
                }

        elif step == "map_targets":
            doors = app_state.stats.get("doors_targeted", 0)
            if doors < 1000:
                return {
                    "text": f"**Next:** Select more zones. You have {doors}/1,000 doors.\n\nDrag the map to Frisco/Plano, select HOT ZIPs from the tactical list.",
                    "actions": ["highlight_map"],
                    "confidence": 0.94,
                }
            else:
                return {
                    "text": "**1,000+ doors targeted.** Ready to build routes.\n\nClick 'Build Routes' to advance.",
                    "actions": ["advance_step"],
                    "confidence": 0.96,
                }

        elif step == "build_routes":
            routes = app_state.routes_created
            if routes < 2:
                return {
                    "text": f"**Next:** Build {2 - routes} more route(s).\n\nClick 'Auto-generate routes' or manually cluster zones.",
                    "actions": ["highlight_button", "build_routes"],
                    "confidence": 0.93,
                }

        elif step == "job_intel":
            claims = app_state.stats.get("claims_filed", 0)
            if claims < 2:
                return {
                    "text": "**Next:** File insurance claims for inspected properties.\n\nSend trust assets (drone clips, photos) to homeowners.",
                    "actions": [],
                    "confidence": 0.92,
                }

        elif step == "nurture_loop":
            return {
                "text": "**Next:** Send review requests to completed jobs.\n\nSchedule annual maintenance checkups for 5-year pipeline.",
                "actions": [],
                "confidence": 0.91,
            }

        return {
            "text": "All systems operational. Ask me anything.",
            "actions": [],
            "confidence": 0.8,
        }

    def _build_system_prompt(self, app_state: AppState) -> str:
        """Build step-aware system prompt with live KPIs and actionable guidance."""
        step = app_state.mission.current_step
        score = app_state.mission.play_score

        prompt = "You are StormOps Copilot, a tactical assistant for post-storm roofing operations.\n\n"

        prompt += "CURRENT MISSION STATE:\n"
        prompt += f"- Phase: {step.upper().replace('_', ' ')}\n"
        prompt += f"- Storm Play Score: {score}/100\n"
        prompt += f"- Doors Targeted: {app_state.stats.get('doors_targeted', 0)}\n"
        prompt += f"- Routes Built: {app_state.routes_created}\n"
        prompt += f"- Claims Filed: {app_state.stats.get('claims_filed', 0)}\n\n"

        prompt += "5-STEP STORMOPS PLAY:\n"
        prompt += "1. DETECTION (Hour 0-2): Load storm, score zones by impact\n"
        prompt += "2. MAP TARGETS (Hour 2-6): Drag map viewport, select hot ZIP+4s\n"
        prompt += "3. BUILD ROUTES (Hour 6-12): Cluster doors, assign crews\n"
        prompt += "4. JOB INTEL (Hour 12-48): Track inspections, file claims, send trust assets\n"
        prompt += (
            "5. NURTURE (Week 1-Year 5): Reviews, referrals, maintenance cadence\n\n"
        )

        # Step-specific guidance
        if step == "detect_storm":
            prompt += "CURRENT OBJECTIVE: Load the hail event and identify hot zones.\n"
            prompt += "NEXT ACTION: Click 'Load event & find targets' to advance to Map Targets.\n"
            prompt += f"TARGET: Score at least {MISSION_THRESHOLDS['detect_storm']['hot_zones']} hot zones.\n\n"

        elif step == "map_targets":
            doors = app_state.stats.get("doors_targeted", 0)
            target_doors = MISSION_THRESHOLDS["map_targets"]["doors"]
            hot_zips = len(
                [
                    z
                    for z in app_state.zones.values()
                    if z.selected and z.risk_level == "High"
                ]
            )
            target_zips = MISSION_THRESHOLDS["map_targets"]["hot_zips"]

            prompt += (
                "CURRENT OBJECTIVE: Select high-impact zones from the tactical list.\n"
            )
            prompt += f"PROGRESS: {doors}/{target_doors} doors, {hot_zips}/{target_zips} HOT ZIPs selected.\n"
            prompt += (
                "NEXT ACTION: Run AI Refinement on selected ZIPs, then build routes.\n"
            )
            prompt += "TIP: Focus on Frisco/Plano/Southlake hot zones to beat competitors.\n\n"

        elif step == "build_routes":
            routes = app_state.routes_created
            target_routes = MISSION_THRESHOLDS["build_routes"]["routes"]

            prompt += (
                "CURRENT OBJECTIVE: Cluster doors into optimized canvassing routes.\n"
            )
            prompt += f"PROGRESS: {routes}/{target_routes} routes built.\n"
            prompt += "NEXT ACTION: Build at least 2 routes with 3+ HOT ZIPs each.\n"
            prompt += "TIP: Use proximity clustering to minimize drive time between doors.\n\n"

        elif step == "job_intel":
            inspected = app_state.stats.get("inspections", 0)
            claims = app_state.stats.get("claims_filed", 0)
            target_inspected = MISSION_THRESHOLDS["job_intel"]["inspected"]
            target_claims = MISSION_THRESHOLDS["job_intel"]["claims"]

            prompt += "CURRENT OBJECTIVE: Document damage and file insurance claims.\n"
            prompt += f"PROGRESS: {inspected}/{target_inspected} inspected, {claims}/{target_claims} claims filed.\n"
            prompt += "NEXT ACTION: Send insurance-help SMS with trust assets (drone clips, photos).\n"
            prompt += "TIP: Contingency agreements remove homeowner risk and accelerate decisions.\n\n"

        elif step == "nurture_loop":
            reviews = app_state.stats.get("reviews_sent", 0)
            target_reviews = MISSION_THRESHOLDS["nurture_loop"]["reviews"]

            prompt += "CURRENT OBJECTIVE: Generate reviews and build 5-year maintenance pipeline.\n"
            prompt += f"PROGRESS: {reviews}/{target_reviews} review requests sent.\n"
            prompt += "NEXT ACTION: Send review requests to completed jobs, schedule annual checkups.\n"
            prompt += (
                "TIP: Every closed job is a 5-year book of business—nurture it.\n\n"
            )

        prompt += "RESPONSE STRUCTURE:\n"
        prompt += "1. What I see: [Current KPIs and bottlenecks]\n"
        prompt += "2. What to do now: [One concrete action]\n"
        prompt += "3. Button to click: [Exact UI element to interact with]\n\n"

        prompt += "GUARDRAILS:\n"
        prompt += "- Only recommend actions available in the current phase\n"
        prompt += "- Reference live KPIs and thresholds in every response\n"
        prompt += "- Use tactical terminology (HOT ZIPs, trust assets, contingency, adjuster)\n"
        prompt += "- Keep responses under 3 sentences\n\n"

        return prompt

    def _fallback_response(self, prompt: str) -> str:
        """Generate a contextual response based on the prompt without external AI."""
        prompt_lower = prompt.lower()

        responses = {
            "greeting": "Hello! I'm StormOps AI. I can help you with lead analysis, route optimization, storm tracking, and operational recommendations. What would you like to know?",
            "lead": "I can analyze your leads by score, tier, location, or conversion probability. Check the Leads tab for detailed scoring with AI confidence levels.",
            "route": "Routes are optimized based on geographic clustering, door density, and estimated lead value. Use the Tactical Map to build and assign routes.",
            "storm": "The current storm event is tracked with real-time hail size, wind speed, and damage propensity scores across all impacted ZIPs.",
            "status": "Your operational status is tracked in the scoreboard. Green indicators show completed tasks, yellow shows in-progress, and red shows blocked.",
            "action": "Recommended actions are prioritized based on highest impact. Review the AI Action Queue for proposed tasks with confidence scores.",
            "score": "Your Storm Play Score is calculated across detection, targeting, routing, and conversion metrics. Higher scores indicate better operational efficiency.",
            "help": "I can help with: lead analysis, route building, storm tracking, TAM calculation, claim filing, and operational recommendations.",
        }

        for key, response in responses.items():
            if key in prompt_lower:
                return response

        return f"""**StormOps AI Assistant**

I understand you're asking about: "{prompt}"

I can help you with:
• Lead analysis and scoring (check the Leads tab)
• Route optimization and crew assignment (Tactical Map)
• Storm tracking and impact assessment (Weather Watcher)
• TAM and revenue analysis (AI Copilot)
• Action recommendations (AI Action Queue)

What specific information do you need?"""
