# StormOps × WeKnora Integration v1.0

## Overview
Use WeKnora as the **document/knowledge brain** for unstructured intelligence, while StormOps remains the **physics/ops control plane** for numerical decisions. WeKnora answers "what to say and what rules apply"; StormOps decides "who/when/where".

**Division of Labor**:
- **StormOps**: Physics (SII, MOE), enrichment (parcels, SES, permits), behavior, proposals, routes
- **WeKnora**: Policy docs, playbooks, scripts, compliance rules, carrier guidelines

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  StormOps Control Plane                                         │
│  - Generates Proposals (who, when, where)                       │
│  - Needs: scripts, policy guidance, compliance checks           │
└────────────────┬────────────────────────────────────────────────┘
                 │ API Call
                 │ Context: SII, SES, playbook, carrier, state
                 │ Task: "Generate compliant SMS", "Policy clauses"
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  WeKnora (RAG + Agent Framework)                                │
│  - Multi-KB retrieval                                           │
│  - Agent reasoning                                              │
│  - Source traceability                                          │
└────────────────┬────────────────────────────────────────────────┘
                 │ Response
                 │ - Generated text/scripts
                 │ - Source documents
                 │ - Confidence scores
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  StormOps Actuation                                             │
│  - Stores scripts in templates table                            │
│  - Logs source docs for traceability                            │
│  - Surfaces in UI sidebar                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## WeKnora Knowledge Bases

### KB 1: Insurance Policies & Carrier Rules

**Content**:
- Policy language (coverage, exclusions, deductibles)
- Carrier-specific hail/roof damage guidelines
- Underwriting rules by carrier
- Xactimate documentation
- Claims process flowcharts

**Use Cases**:
- "What does Carrier X cover for hail damage on composition shingles in TX?"
- "What's the deductible structure for wind + hail claims?"
- "Generate a claim summary for a 1.75" hail event on a 15-year-old roof"

**Sample Documents**:
```
kb_insurance/
├── carriers/
│   ├── state_farm_hail_guidelines.pdf
│   ├── allstate_roof_coverage.pdf
│   └── farmers_wind_hail_policy.pdf
├── xactimate/
│   ├── roofing_line_items.pdf
│   └── pricing_guide_2026.pdf
└── claims_process/
    ├── hail_claim_workflow.md
    └── documentation_requirements.pdf
```

### KB 2: Playbooks & SOPs

**Content**:
- Strategic play specifications (Frisco-Alpha, Loyalty-DFW, etc.)
- Targeting rules and channel strategies
- Training guides for reps
- Objection-handling scripts
- Quality checklists

**Use Cases**:
- "What's the targeting logic for Frisco-Alpha playbook?"
- "Generate an objection-handling script for price concerns in high-SES neighborhoods"
- "What's the SOP for door-knock timing in residential areas?"

**Sample Documents**:
```
kb_playbooks/
├── strategic_plays/
│   ├── frisco_alpha_v1.2.md
│   ├── loyalty_dfw_highses_v1.0.md
│   └── expansion_lookalike_v1.1.md
├── scripts/
│   ├── sms_templates_by_persona.md
│   ├── phone_scripts_emotional.md
│   └── door_knock_openers.md
├── training/
│   ├── new_rep_onboarding.pdf
│   └── objection_handling_guide.md
└── sops/
    ├── canvassing_best_practices.md
    └── inspection_checklist.pdf
```

### KB 3: Legal & Compliance

**Content**:
- TCPA regulations (consent, quiet hours, frequency limits)
- State-specific canvassing laws
- FAA Part 107 drone rules
- Insurance licensing requirements
- Data privacy regulations (CCPA, etc.)

**Use Cases**:
- "What are the TCPA requirements for SMS in Texas?"
- "Can we door-knock on Sundays in Dallas?"
- "What consent language do we need for phone calls?"
- "What are the FAA rules for commercial drone roof inspections?"

**Sample Documents**:
```
kb_compliance/
├── tcpa/
│   ├── tcpa_overview.pdf
│   ├── consent_requirements.md
│   └── state_specific_rules.pdf
├── canvassing/
│   ├── texas_solicitation_laws.pdf
│   └── city_ordinances_dallas.pdf
├── drones/
│   ├── part_107_summary.pdf
│   └── commercial_operations_guide.pdf
└── privacy/
    ├── ccpa_compliance.md
    └── data_retention_policy.md
```

### KB 4: Competitor Intelligence

**Content**:
- Competitor playbooks (observed patterns)
- Pricing strategies by market
- Marketing materials analysis
- Win/loss analysis notes

**Use Cases**:
- "What tactics is ABC Roofing using in Frisco?"
- "How should we position against Competitor X's pricing?"
- "What are common reasons we lose to Competitor Y?"

**Sample Documents**:
```
kb_competitors/
├── profiles/
│   ├── abc_roofing_analysis.md
│   ├── xyz_contractors_tactics.md
│   └── rapid_roof_pricing.md
├── win_loss/
│   ├── q4_2025_analysis.md
│   └── common_objections.md
└── marketing/
    ├── competitor_ads_analysis.pdf
    └── messaging_comparison.md
```

---

## API Integration

### StormOps → WeKnora Request

**Endpoint**: `POST /api/v1/query`

**Request Schema**:
```json
{
  "context": {
    "property_id": "prop_12345",
    "sii_score": 82,
    "ses_tier": "High",
    "persona": "Family_Protector",
    "playbook_id": "frisco-alpha",
    "carrier": "State Farm",
    "state": "TX",
    "city": "Dallas",
    "roof_age_years": 15,
    "roof_material": "Composition Shingle"
  },
  "task": {
    "type": "generate_script",
    "channel": "sms",
    "tone": "emotional",
    "constraints": ["tcpa_compliant", "max_160_chars"]
  },
  "knowledge_bases": ["kb_playbooks", "kb_compliance"]
}
```

**Response Schema**:
```json
{
  "result": {
    "text": "Hi [Name], we noticed recent hail damage in your area. Your family's safety is our priority. Free inspection available this week. Reply YES for details.",
    "metadata": {
      "char_count": 158,
      "tcpa_compliant": true,
      "tone_match": 0.92
    }
  },
  "sources": [
    {
      "kb": "kb_playbooks",
      "document": "sms_templates_by_persona.md",
      "section": "Family Protector - Emotional",
      "relevance_score": 0.95
    },
    {
      "kb": "kb_compliance",
      "document": "tcpa_overview.pdf",
      "section": "SMS Consent Requirements",
      "relevance_score": 0.88
    }
  ],
  "confidence": 0.91
}
```

### Example API Calls

#### 1. Generate SMS Script

```python
import requests

def generate_sms_script(property_context: dict) -> dict:
    """Generate TCPA-compliant SMS script via WeKnora."""
    
    response = requests.post('http://weknora:8000/api/v1/query', json={
        "context": {
            "property_id": property_context['property_id'],
            "sii_score": property_context['sii_score'],
            "ses_tier": property_context['ses_tier'],
            "persona": property_context['persona'],
            "state": property_context['state']
        },
        "task": {
            "type": "generate_script",
            "channel": "sms",
            "tone": property_context['preferred_tone'],
            "constraints": ["tcpa_compliant", "max_160_chars"]
        },
        "knowledge_bases": ["kb_playbooks", "kb_compliance"]
    })
    
    return response.json()

# Usage
property = {
    'property_id': 'prop_12345',
    'sii_score': 82,
    'ses_tier': 'High',
    'persona': 'Family_Protector',
    'preferred_tone': 'emotional',
    'state': 'TX'
}

script_result = generate_sms_script(property)
print(script_result['result']['text'])
print(f"Sources: {len(script_result['sources'])}")
```

#### 2. Policy Clause Lookup

```python
def get_policy_guidance(carrier: str, damage_type: str, roof_material: str, state: str) -> dict:
    """Get carrier-specific policy guidance."""
    
    response = requests.post('http://weknora:8000/api/v1/query', json={
        "context": {
            "carrier": carrier,
            "damage_type": damage_type,
            "roof_material": roof_material,
            "state": state
        },
        "task": {
            "type": "policy_lookup",
            "question": f"What does {carrier} cover for {damage_type} on {roof_material} roofs in {state}?"
        },
        "knowledge_bases": ["kb_insurance"]
    })
    
    return response.json()

# Usage
guidance = get_policy_guidance(
    carrier="State Farm",
    damage_type="hail",
    roof_material="composition shingle",
    state="TX"
)
print(guidance['result']['text'])
```

#### 3. Compliance Check

```python
def check_compliance(action: str, context: dict) -> dict:
    """Check if action is compliant with regulations."""
    
    response = requests.post('http://weknora:8000/api/v1/query', json={
        "context": context,
        "task": {
            "type": "compliance_check",
            "action": action,
            "regulations": ["tcpa", "state_solicitation"]
        },
        "knowledge_bases": ["kb_compliance"]
    })
    
    return response.json()

# Usage
compliance = check_compliance(
    action="door_knock",
    context={
        "day_of_week": "Sunday",
        "time": "10:00",
        "city": "Dallas",
        "state": "TX",
        "has_consent": False
    }
)
print(f"Compliant: {compliance['result']['compliant']}")
print(f"Reason: {compliance['result']['reason']}")
```

#### 4. Playbook Retrieval

```python
def get_playbook_details(playbook_name: str) -> dict:
    """Retrieve playbook specification."""
    
    response = requests.post('http://weknora:8000/api/v1/query', json={
        "context": {
            "playbook_name": playbook_name
        },
        "task": {
            "type": "playbook_lookup",
            "fields": ["targeting_rules", "channel_strategy", "kpis"]
        },
        "knowledge_bases": ["kb_playbooks"]
    })
    
    return response.json()

# Usage
playbook = get_playbook_details("frisco-alpha")
print(playbook['result']['targeting_rules'])
```

---

## StormOps Integration Points

### 1. Proposal Generation

**When**: StormOps creates a Proposal  
**What**: Fetch appropriate script/template from WeKnora

```python
# proposal_engine.py
def create_proposal_with_script(property_id: str, playbook_id: str):
    """Create proposal with WeKnora-generated script."""
    
    # Get property context from StormOps
    property = get_property_context(property_id)
    playbook = get_playbook(playbook_id)
    
    # Generate script via WeKnora
    script_result = generate_sms_script({
        'property_id': property_id,
        'sii_score': property['sii_score'],
        'ses_tier': property['ses_tier'],
        'persona': property['persona'],
        'preferred_tone': property['preferred_tone'],
        'state': property['state']
    })
    
    # Create proposal
    proposal = {
        'property_id': property_id,
        'playbook_id': playbook_id,
        'script': script_result['result']['text'],
        'script_sources': script_result['sources'],
        'script_confidence': script_result['confidence'],
        'created_at': datetime.now()
    }
    
    # Store in Postgres
    insert_proposal(proposal)
    
    return proposal
```

### 2. Pre-Contact Compliance Check

**When**: Before executing any contact action  
**What**: Verify compliance via WeKnora

```python
# actuation.py
def execute_contact_action(proposal_id: str):
    """Execute contact action with compliance check."""
    
    proposal = get_proposal(proposal_id)
    property = get_property(proposal['property_id'])
    
    # Check compliance
    compliance = check_compliance(
        action=proposal['channel'],
        context={
            'day_of_week': datetime.now().strftime('%A'),
            'time': datetime.now().strftime('%H:%M'),
            'city': property['city'],
            'state': property['state'],
            'has_consent': property['has_sms_consent']
        }
    )
    
    if not compliance['result']['compliant']:
        log_blocked_action(proposal_id, compliance['result']['reason'])
        return {'status': 'blocked', 'reason': compliance['result']['reason']}
    
    # Execute action
    send_sms(property['phone'], proposal['script'])
    
    return {'status': 'sent'}
```

### 3. Impact Report Generation

**When**: Creating customer-facing damage reports  
**What**: Get policy guidance and claim process info

```python
# impact_reports.py
def generate_impact_report(property_id: str, event_id: str):
    """Generate impact report with policy guidance."""
    
    property = get_property(property_id)
    exposure = get_property_exposure(property_id, event_id)
    
    # Get policy guidance
    policy_guidance = get_policy_guidance(
        carrier=property['insurance_carrier'],
        damage_type='hail',
        roof_material=property['roof_material'],
        state=property['state']
    )
    
    report = {
        'property_id': property_id,
        'sii_score': exposure['sii_score'],
        'moe_usd': exposure['moe_usd'],
        'policy_coverage': policy_guidance['result']['text'],
        'policy_sources': policy_guidance['sources'],
        'next_steps': generate_next_steps(property, exposure),
        'generated_at': datetime.now()
    }
    
    return report
```

### 4. Objection Handling

**When**: Rep encounters objection during call/visit  
**What**: Real-time script suggestions from WeKnora

```python
# real_time_assist.py
def get_objection_response(objection_type: str, context: dict) -> dict:
    """Get real-time objection handling script."""
    
    response = requests.post('http://weknora:8000/api/v1/query', json={
        "context": context,
        "task": {
            "type": "objection_handling",
            "objection": objection_type,
            "tone": context.get('preferred_tone', 'professional')
        },
        "knowledge_bases": ["kb_playbooks"]
    })
    
    return response.json()

# Usage in Streamlit UI
if st.button("Price Objection"):
    response = get_objection_response(
        objection_type="price_too_high",
        context={
            'ses_tier': 'High',
            'persona': 'Deal_Hunter',
            'competitor_quote': 15000,
            'our_quote': 17000
        }
    )
    st.write(response['result']['text'])
```

---

## Traceability Schema

### Store WeKnora Sources in Postgres

```sql
CREATE TABLE proposal_knowledge_sources (
    source_id UUID PRIMARY KEY,
    proposal_id UUID REFERENCES proposals(proposal_id),
    
    -- WeKnora response
    kb_name TEXT,
    document_name TEXT,
    document_section TEXT,
    relevance_score DECIMAL(3, 2),
    
    -- Content
    retrieved_text TEXT,
    
    -- Metadata
    query_timestamp TIMESTAMP,
    confidence_score DECIMAL(3, 2),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_proposal (proposal_id),
    INDEX idx_kb (kb_name)
);
```

### Log Every WeKnora Call

```python
def log_weknora_query(proposal_id: str, query: dict, response: dict):
    """Log WeKnora query for traceability."""
    
    for source in response['sources']:
        insert_knowledge_source({
            'proposal_id': proposal_id,
            'kb_name': source['kb'],
            'document_name': source['document'],
            'document_section': source.get('section'),
            'relevance_score': source['relevance_score'],
            'retrieved_text': source.get('text', ''),
            'query_timestamp': datetime.now(),
            'confidence_score': response['confidence']
        })
```

---

## WeKnora Deployment

### Docker Compose (Sidecar to StormOps)

```yaml
# docker-compose.yml
services:
  # Existing StormOps services...
  
  weknora:
    image: weknora/weknora:latest
    ports:
      - "8000:8000"
    environment:
      - WEKNORA_MODE=production
      - VECTOR_DB=milvus
      - GRAPH_DB=neo4j
      - STORAGE=minio
    volumes:
      - ./weknora_data:/data
    depends_on:
      - milvus
      - neo4j
      - minio
```

### Initialize Knowledge Bases

```bash
# Create KBs
curl -X POST http://localhost:8000/api/v1/kb/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kb_insurance",
    "description": "Insurance policies and carrier guidelines",
    "embedding_model": "text-embedding-3-small"
  }'

curl -X POST http://localhost:8000/api/v1/kb/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kb_playbooks",
    "description": "Strategic playbooks and SOPs"
  }'

curl -X POST http://localhost:8000/api/v1/kb/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kb_compliance",
    "description": "Legal and compliance documentation"
  }'

curl -X POST http://localhost:8000/api/v1/kb/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kb_competitors",
    "description": "Competitor intelligence"
  }'
```

### Upload Documents

```python
# upload_docs.py
import requests
import os

def upload_documents_to_kb(kb_name: str, docs_dir: str):
    """Upload all documents in directory to WeKnora KB."""
    
    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            if file.endswith(('.pdf', '.md', '.txt', '.docx')):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'rb') as f:
                    response = requests.post(
                        f'http://localhost:8000/api/v1/kb/{kb_name}/upload',
                        files={'file': f}
                    )
                    
                    if response.status_code == 200:
                        print(f"Uploaded: {file}")
                    else:
                        print(f"Failed: {file} - {response.text}")

# Upload all KBs
upload_documents_to_kb('kb_insurance', './docs/insurance/')
upload_documents_to_kb('kb_playbooks', './docs/playbooks/')
upload_documents_to_kb('kb_compliance', './docs/compliance/')
upload_documents_to_kb('kb_competitors', './docs/competitors/')
```

---

## Airflow Sync Job

**Keep WeKnora KBs updated with latest docs**:

```python
# dags/sync_weknora_kb_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def sync_playbooks_to_weknora():
    """Sync updated playbook docs to WeKnora."""
    # Check for updated playbook files
    updated_files = get_updated_files('./docs/playbooks/', since_hours=24)
    
    for file_path in updated_files:
        # Re-upload to WeKnora
        with open(file_path, 'rb') as f:
            requests.post(
                'http://weknora:8000/api/v1/kb/kb_playbooks/upload',
                files={'file': f}
            )
    
    print(f"Synced {len(updated_files)} playbook documents")

with DAG(
    'sync_weknora_kbs',
    default_args={'owner': 'stormops'},
    schedule_interval='0 */6 * * *',  # Every 6 hours
    start_date=datetime(2026, 1, 1),
    catchup=False
) as dag:
    
    sync_playbooks = PythonOperator(
        task_id='sync_playbooks',
        python_callable=sync_playbooks_to_weknora
    )
    
    sync_compliance = PythonOperator(
        task_id='sync_compliance',
        python_callable=sync_compliance_to_weknora
    )
    
    [sync_playbooks, sync_compliance]
```

---

## Summary

### Division of Labor

| Component | Owns | Example |
|-----------|------|---------|
| **StormOps** | Who, when, where | "Contact property_12345 at 6 PM via SMS" |
| **WeKnora** | What to say, what rules | "Use this script: [text]. TCPA compliant per [doc]" |

### Integration Points

1. **Proposal generation** → Fetch scripts
2. **Pre-contact** → Compliance check
3. **Impact reports** → Policy guidance
4. **Real-time assist** → Objection handling

### Traceability

Every WeKnora response logged with:
- Source documents
- Relevance scores
- Confidence levels
- Linked to proposals

### Deployment

WeKnora runs as sidecar service:
- Same Docker Compose as StormOps
- Shares Milvus, Neo4j, MinIO
- Synced via Airflow every 6 hours

---

## Next Steps

1. Deploy WeKnora alongside StormOps stack
2. Create 4 knowledge bases
3. Upload initial document corpus
4. Integrate API calls into proposal engine
5. Add traceability logging
6. Set up Airflow sync job
7. Test end-to-end: Proposal → WeKnora → Script → Execution

---

This gives StormOps a **document brain** without diluting its core strength as a physics/ops engine. WeKnora handles messy unstructured knowledge; StormOps handles precise numerical decisions.
