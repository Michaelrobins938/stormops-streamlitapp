# StormOps Product Requirements Document (PRD)

## 1. Product Vision
StormOps is a **storm-driven operating console** for roofing companies that turns real-time weather (Earth-2), property data, and AI into a guided 5-step workflow: from "storm hits" to "closed, claim-driven replacements and 5-year nurture." 

## 2. Problem Statement
Roofing teams struggle with:
- Deciding which storms are worth chasing.
- Inefficient canvassing and poorly targeted digital spend.
- Fragmented tracking of jobs and claims.
- Weak long-term customer retention and referral engines.

## 3. Target Personas
- **Owner / GM:** Strategic decision-making and high-level KPI tracking.
- **Sales Manager:** Route building, rep assignment, and funnel management.
- **Field Rep:** Execution of door-knocking and lead capture.

## 4. Functional Requirements

### 5.1 Detection & Storm Intel (Phase 1)
- **FR-D1:** Ingest Earth-2 data and produce DFW storm events.
- **FR-D2:** Compute a per-zone **Impact Index** (hail size, duration, roof inventory).
- **FR-D3:** Display tactical map with Impact Index and Nowcast ETA overlays.
- **FR-D4:** Gate transition to Map Targets phase.

### 5.2 Map Targets (Phase 2)
- **FR-M1:** Build Tactical list based on map viewport bounds.
- **FR-M2:** Zone scoring with Impact Index, ETA, and property stats.
- **FR-M3:** Sortable/filterable Tactical list UI with status badges.
- **FR-M4:** Threshold-based completion checks (min zones/doors).

### 5.3 Build Routes (Phase 3)
- **FR-R1:** Automatic route generation with door counts and est. value.
- **FR-R2:** Route cards showing drive time and assignment status.
- **FR-R3:** Route optimization and re-clustering.
- **FR-R4:** Coverage-based completion checks.

### 5.4 Job Intelligence (Phase 4)
- **FR-J1:** Comprehensive Job entity (Address, Type, Claim status, Trust assets).
- **FR-J2:** Full funnel tracking (Knocks -> Leads -> Inspections -> Claims -> Wins).
- **FR-J3:** Bottleneck detection highlighting stuck jobs.
- **FR-J4:** Manual and AI-assisted job stage advancement.

### 5.5 Nurture (Phase 5)
- **FR-N1:** 5-year maintenance journey enrollment for closed jobs.
- **FR-N2:** Automated review and referral request triggers.
- **FR-N3:** Nurture task queue management.
- **FR-N4:** CRM synchronization (JobNimbus/CSV).

### 5.6 AI Operational Assistant
- **FR-C1:** Step-aware Copilot utilizing canonical `AppState`.
- **FR-C2:** Tooling for zone prioritization, script generation, and channel mix recommendations.
- **FR-C3:** Strict UI guardrails to prevent data fabrication.

## 5. Non-Functional Requirements
- **Performance:** Storm load < 5s; Interaction response < 2s.
- **Resilience:** Graceful fallbacks for API outages.
- **Security:** Standard encryption for PII; authenticated access.
- **UX:** Intuitive navigation allowing first route build in < 10 mins.

## 6. Success Metrics
- **Business:** Increased jobs per storm; improved knock-to-win conversion.
- **Product:** Route build volume; Copilot suggestion acceptance; 5-step completion rate.
