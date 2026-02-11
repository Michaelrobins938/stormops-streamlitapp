# StormOps Architecture Map

## Core Modules

### 1. Application Shell (`app.py`)
- **Responsibility:** Entrypoint, UI routing (Streamlit), Session State management, coordination between AI and Services.
- **Imports:** `state.py`, `roofing_ai.py`, `services/*`, `earth2_downscale.py`.
- **Exports:** Streamlit UI, JSON state for React.
- **Used by:** End users (Roofer/Admin).

### 2. AI Intelligence (`roofing_ai.py`)
- **Responsibility:** Copilot logic, intent classification, prompt construction, tool execution.
- **Imports:** `state.py`, `services/*`.
- **Exports:** `RoofingAIAssistant` class.
- **Used by:** `app.py`, `api.py`.

### 3. Services Layer (`services/`)
- **`earth2_service.py`**: Interacts with NVIDIA Earth-2/GFS data.
- **`property_service.py`**: Interacts with ATTOM/Property data.
- **`crm_service.py`**: Interacts with JobNimbus/Mock CRM.
- **Responsibility:** External API abstractions and data fetching.
- **Used by:** `roofing_ai.py`, `app.py`.

### 4. Logic & Analytics
- **`earth2_downscale.py`**: Physics-informed CorrDiff super-resolution simulation.
- **`roof_risk_index.py`**: Cumulative damage scoring logic.

### 5. Frontend (`frontend/`)
- **Responsibility:** React shell, Map (Mapbox), Mission navigation, high-performance UI components.
- **Communicates via:** FastAPI (`api.py`) and Streamlit embeds.

## Data Flow (Wiring)
1. **Storm Event** -> `Earth2Service` fetches coarse data.
2. **Refinement** -> `StormDownscaler` (earth2_downscale) computes Impact Index.
3. **Targeting** -> `PropertyService` joins weather with roof value.
4. **State** -> All updates write to a canonical `AppState` object.
5. **AI** -> `RoofingAIAssistant` reasons over `AppState` to suggest next moves.
