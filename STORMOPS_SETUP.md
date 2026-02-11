# StormOps v1 Setup Guide

## Stage 1: Data & Scoring Foundation (COMPLETE)

### Files Created

1. **stormops_schema.sql** – PostgreSQL + PostGIS database schema
2. **sii_scorer.py** – StormOps Impact Index scoring function
3. **earth2_ingestion.py** – Earth-2 hail field ingestion pipeline
4. **load_test_data.py** – Test data loader for 75034 (Frisco)

### Quick Start

#### 1. Set up PostgreSQL + PostGIS

```bash
# Install PostgreSQL and PostGIS (if not already installed)
sudo apt-get install postgresql postgresql-contrib postgis

# Start PostgreSQL
sudo service postgresql start

# Create database
sudo -u postgres createdb stormops
sudo -u postgres psql -d stormops -c "CREATE EXTENSION postgis;"
```

#### 2. Load schema

```bash
sudo -u postgres psql -d stormops -f stormops_schema.sql
```

#### 3. Load test data

```bash
cd /home/forsythe/earth2-forecast-wsl/hotspot_tool
python3 load_test_data.py
```

Expected output:
```
Created event: <event-id>
Inserted 4200 parcels
Inserted 4200 impact scores
Parcels with SII >= 60: ~1680
```

#### 4. Verify data

```bash
sudo -u postgres psql -d stormops -c "
SELECT COUNT(*) as total_parcels,
       COUNT(CASE WHEN sii_score >= 60 THEN 1 END) as high_sii,
       AVG(sii_score) as avg_sii
FROM impact_scores;
"
```

---

## Stage 2: Lead Gen & Route Building (IN PROGRESS)

### Files Created

1. **crm_integration.py** – ServiceTitan/JobNimbus API client
2. **proposal_engine.py** – Generates executable Proposals
3. **route_optimizer.py** – TSP-based route builder
4. **stormops_ui.py** – Minimal Streamlit UI

### Quick Start

#### 1. Install dependencies

```bash
pip install streamlit psycopg2-binary numpy requests
```

#### 2. Update database credentials

Edit the following files and set your PostgreSQL credentials:
- `crm_integration.py` (line ~10)
- `proposal_engine.py` (line ~20)
- `route_optimizer.py` (line ~20)
- `stormops_ui.py` (line ~20)

#### 3. Run the UI

```bash
cd /home/forsythe/earth2-forecast-wsl/hotspot_tool
streamlit run stormops_ui.py
```

Open browser to `http://localhost:8501`

#### 4. Test the workflow

1. **Select Event** – Choose "DFW Storm 24" from sidebar
2. **Generate Leads** – Click "Generate Leads Now" (creates lead gen proposal)
3. **Build Routes** – Click "Build Routes Now" (creates 4 optimized routes)
4. **Send SMS** – Click "Send SMS Campaign" (creates SMS proposal)
5. **Approve Proposals** – Click "Approve" on each proposal in the queue

Expected results:
- ~1,680 leads generated for 75034 with SII >= 60
- 4 optimized canvassing routes with ~50 roofs each
- SMS campaign queued for ~800 past customers

---

## Stage 3: Operational Intelligence (NEXT)

### To Build

1. **MOE (Markov Opportunity Engine)** – State machine for Baseline → Risk → Impact → Recovery
2. **Impact Report Generator** – Physics-backed reports for each parcel
3. **SLA & Quality Monitor** – Track time-to-first-contact, rep adherence
4. **Forecast Monitoring** – Automated alerts for forecast threshold breaches

---

## Database Schema Overview

### Core Tables

- **events** – Storm events (DFW Storm 24, etc.)
- **parcels** – Individual roofs/properties in DFW
- **impact_scores** – SII scores per parcel per event
- **leads** – Generated leads from event + SII scoring
- **routes** – Canvassing routes for field reps
- **proposals** – Executable actions (lead gen, route build, SMS)
- **moe_state** – Markov Opportunity Engine state per sector
- **impact_reports** – Pre-built physics-backed reports

### Key Queries

```sql
-- Get top 1,680 parcels in 75034 with SII >= 60
SELECT p.parcel_id, p.address, is.sii_score, is.hail_intensity_mm
FROM impact_scores is
JOIN parcels p ON is.parcel_id = p.id
WHERE p.zip_code = '75034' AND is.sii_score >= 60
ORDER BY is.sii_score DESC
LIMIT 1680;

-- Get all pending proposals
SELECT id, proposal_type, target_zip, expected_leads, expected_value_usd
FROM proposals
WHERE status = 'pending'
ORDER BY expected_value_usd DESC;

-- Get routes for an event
SELECT id, route_name, parcel_count, status
FROM routes
WHERE event_id = '<event-id>'
ORDER BY created_at DESC;
```

---

## SII Scoring Details

The StormOps Impact Index (SII) combines:

1. **Hail Intensity** – Hail diameter in mm (from Earth-2)
2. **Roof Material** – asphalt, metal, tile, wood, composite
3. **Roof Age** – Age in years (older = more vulnerable)

### Damage Thresholds (mm)

- Asphalt: 20mm (~0.8")
- Metal: 32mm (~1.25")
- Tile: 38mm (~1.5")
- Wood: 25mm (~1")
- Composite: 22mm (~0.9")

### Material Vulnerability

- Asphalt: 1.0 (baseline)
- Metal: 0.6 (more resistant)
- Tile: 0.7 (moderately resistant)
- Wood: 1.2 (more vulnerable)
- Composite: 0.9 (slightly less vulnerable)

### Age Degradation

- 2% increase in vulnerability per year
- 20-year roof is ~1.4x more vulnerable than new roof

---

## Troubleshooting

### PostgreSQL Connection Error

```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
1. Check PostgreSQL is running: `sudo service postgresql status`
2. Verify credentials in code
3. Check database exists: `sudo -u postgres psql -l | grep stormops`

### PostGIS Extension Error

```
ERROR: extension "postgis" does not exist
```

**Solution:**
```bash
sudo -u postgres psql -d stormops -c "CREATE EXTENSION postgis;"
```

### Streamlit Port Already in Use

```
Address already in use
```

**Solution:**
```bash
streamlit run stormops_ui.py --server.port 8502
```

---

## Next Steps

1. **Integrate with real Earth-2 API** – Replace mock hail fields with live Earth-2 data
2. **Connect to ServiceTitan/JobNimbus** – Replace MockCRMIntegration with real API calls
3. **Build MOE state machine** – Implement Markov chain for Baseline → Risk → Impact → Recovery
4. **Add Impact Report generation** – Create physics-backed reports for high-SII roofs
5. **Deploy to production** – Set up cloud infrastructure (AWS, GCP, etc.)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    StormOps v1 Architecture                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Earth-2 API                                                 │
│      ↓                                                        │
│  earth2_ingestion.py ──→ PostgreSQL + PostGIS               │
│      ↓                        ↓                              │
│  sii_scorer.py ──→ impact_scores table                      │
│                        ↓                                     │
│  proposal_engine.py ──→ proposals table                     │
│      ↓                        ↓                              │
│  route_optimizer.py ──→ routes table                        │
│      ↓                        ↓                              │
│  crm_integration.py ──→ ServiceTitan/JobNimbus             │
│      ↓                        ↓                              │
│  stormops_ui.py ──→ Streamlit Dashboard                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Performance Targets

- **Lead Generation:** 400–600 leads in 2 minutes
- **Route Building:** 4 optimized routes in 5 minutes
- **SMS Campaign:** 800 messages sent in 3 minutes
- **Total Pipeline:** From event to field reps in 60 minutes

---

## Support

For issues or questions, check the logs:

```bash
# Streamlit logs
tail -f ~/.streamlit/logs/2024-*.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```
