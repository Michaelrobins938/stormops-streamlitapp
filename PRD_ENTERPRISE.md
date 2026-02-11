# StormOps: Physics-Native Control Plane for Enterprise Roofing
## Product Requirements Document v2.0

---

## 1. Product Narrative

StormOps is a **physics-native control plane** for enterprise roofing contractors (>$10M revenue) competing in hail-exposed markets. It fuses NVIDIA Earth-2 km-scale digital twin data, parcel intelligence, and CRM events into a single operating picture so operators can see, decide, and act on storm damage at the block and roof level in near real time.

Where traditional tools show weather "near" a ZIP code, StormOps runs a sovereign, DFW-specific digital twin that translates extreme weather into a portfolio of micro-markets, each with a measurable probability of damage, expected claim yield, and recommended human capital deployment. This turns hail events from reactive chaos into scheduled, physics-backed campaigns.

---

## 2. Strategic Moat: "NVIDIA-Standard" Industrial OS

### Block-Level Market Creation
Earth-2 CorrDiff downscales from coarse grids to km-scale fields, capturing local extremes that traditional radar smears out. StormOps treats each 1 km² swath with high damage probability as its own "trade block" with expected revenue, canvassing priority, and staffing recommendations.

### Physics-Synced Revenue Graph
Hail intensity, wind, roof material, and age flow into a physics-backed impact function. Every opportunity, job, and invoice in ServiceTitan/JobNimbus carries a storm event ID and impact index, creating an auditable graph from atmosphere to revenue.

### Agentic Control Plane (AI With Hands)
Instead of chat-only assistants, StormOps exposes the AI as executable Proposals that can launch routes, send SMS/email, and create or move jobs in the CRM. Human operators approve or amend these actions, but the system manages orchestration and timing.

### Stochastic Opportunity Engine
A Markov chain models each sector's state transition from Baseline → Risk → Impact → Recovery with associated claim count and claim value expectations. This lets StormOps surge-allocate crews, pay, and spend into 24-72h "peak money windows" and stand down elsewhere.

### Sovereign Deployment
Earth-2 APIs can be deployed as tenant-specific digital twins, giving large contractors or PE roll-ups a sovereign climate OS for their footprint. StormOps binds that climate twin to private CRM and parcel data, forming a defensible, non-commoditized data asset.

---

## 3. System Overview

StormOps v1 for DFW is a three-pane industrial OS:

### Pane A – Market Observability
Live "Operational Score" (0-100) per sector derived from Earth-2 hazard fields, event recency, MOE state, installed base saturation, and CRM activity density. Answers: "Where is the money right now, and which playbook phase is active?"

### Pane B – Field Operations Map
High-resolution geospatial map with CorrDiff overlays, parcel polygons, and real-time GPS for field reps. Clicking a parcel reveals hail size, impact index, roof age class, and CRM status. Canvas for route construction, geofenced lead intake, and sector definitions.

### Pane C – Agentic Control Rail
Vertical queue of executable Proposals (routes, SMS campaigns, script pushes, job creation) each with preconditions, blast radius, and expected value uplift. Example: "50mm hail detected in Block FRS-12; deploy 'Frisco-Alpha' route (18 roofs, est. $X pipeline)?"

---

## 4. Core Engines

### 4.1 Markov Opportunity Engine (MOE)

**States:**
- **S₀ Baseline:** No elevated storm signal. Actions: CRM hygiene, data enrichment, targeted brand building
- **S₁ Risk:** >80% storm probability in 12h for a sector; trigger "Coming Storm" campaigns and queue canvassing teams
- **S₂ Impact:** Active storm and/or confirmed hail footprint; generate real-time "damage swaths" and open geofenced lead capture
- **S₃ Recovery:** 24-72h post-event, historically associated with peak claim filing and inspection demand

**Outputs:**
For each sector: next-state probabilities over 72h, expected claim count and value band, recommended headcount for canvassers/inspectors, and surge multipliers for comp and ad spend.

### 4.2 StormOps Impact Index (SII)

**Definition:**
A 0-100 scalar per roof combining CorrDiff hail intensity, hailstone mechanics, roof material, and age, inspired by open hail damage models that estimate risk at building level.

**Usage:**
- Drives lead scoring and prioritization
- Powers "Impact Reports" used with homeowners and adjusters
- Feeds MOE and Operational Score so damage severity and revenue projections are coherent

---

## 5. Feature Specifications

### 5.1 Tactical Map
- 1 km (or finer) Earth-2 overlays for hail, wind, and heavy rain intensity
- Parcel click reveals: SII, hail size band, timestamp of peak impact, inferred roof age/material, CRM entity, and MOE state trajectory

### 5.2 Agentic Scripter
- Script generator conditioned on physics (SII, hail size, timing) and persona (homeowner segment, past customer vs net new)
- Produces "Scientific First" or "Empathy First" variants
- Hooks into CRM proposal builders

### 5.3 SLA & Quality Monitor
- Configurable SLAs (e.g., 15 minutes from lead creation to first outreach)
- Timers surfaced as Proposals when breaches occur
- Optional call/audio linkage to CRM call recordings for audit

### 5.4 CRM & Workflow Integrations
- Deep integration with ServiceTitan/JobNimbus for customers, jobs, estimates, invoices, and forms
- Digital forms or checklists triggered for high-SII jobs to enforce inspection protocol

---

## 6. Technical Architecture

### 6.1 Data & Compute
- **Climate/Weather:** Earth-2 APIs (CorrDiff-like km-scale models, medium-range forecasts) on DGX Cloud or equivalent GPU infra
- **Hail & Damage Modeling:** Radar-based hail indices and Bayesian hail damage models to refine SII calibration
- **Spatial Storage:** PostgreSQL + PostGIS for parcel geometries, block sectors, and route computations across >100k DFW parcels

### 6.2 Services
- **Ingestion Service:** Pulls Earth-2 fields, densifies onto DFW grid, writes hazard fields and MOE state updates
- **Scoring Service:** Computes/updates SII per parcel; flags parcels crossing critical thresholds
- **Proposal Engine:** Generates, ranks, and lifecycle-manages Proposals; exposes via Agentic Control Rail and APIs
- **Integration Layer:** Handles CRM sync, webhooks, and auth; ensures job creations and stage changes are mirrored

---

## 7. Business Outcomes & KPIs

### Speed-to-Lead Uplift
Target 4× improvement in close rates by compressing median first contact from ~2 hours toward 10-15 minutes

### Claim Acceptance Lift
Target ~25% relative reduction in claim rejections by pairing claims with structured, physics-backed Impact Reports

### Route Density & Productivity
Target 15% reduction in travel time via high-density routes in top-SII blocks, enabling 1-2 additional inspections per rep per day

### Data Asset Growth
With each event, SII vs real claims and job outcomes become training data, improving future forecasts and forming a proprietary hail-to-revenue dataset

---

## 8. Assumptions, Risks, and Fallbacks

### Weather Data Latency
- **Assumption:** Earth-2 APIs deliver sub-minute updates during severe weather
- **Fallback:** Degraded mode using standard NWP/NOAA feeds and coarser hail indices with transparent indicators

### Sales Script Preference
- **Assumption:** Homeowners respond positively to scientific framing
- **Fallback:** A/B testing infrastructure with fast switching between scientific, empathy-led, and social-proof narratives

### Operational Change Management
- **Assumption:** Contractors will adopt control-plane style workflow vs purely rep-driven decisions
- **Mitigation:** Start with "decision-support only" mode, then progressively enable "click-to-act" Proposals once trust and guardrails are in place

---

## 9. Target Audiences

### For Investors/PE
- Defensible data moat (physics + proprietary claim outcomes)
- 4× speed-to-lead ROI with measurable attribution
- Scalable to multi-market roll-ups with sovereign deployment model

### For Lighthouse DFW Roofing Logo
- Immediate operational advantage in next storm event
- Physics-backed credibility with adjusters and homeowners
- Reduced chaos, increased predictability in revenue timing

### For NVIDIA Ecosystem
- Reference implementation of Earth-2 → enterprise revenue pipeline
- Demonstrates "AI with hands" control plane pattern
- Validates sovereign digital twin deployment model for vertical industries

---

**Document Version:** 2.0  
**Last Updated:** 2026-02-07  
**Status:** Production-Ready
