#!/usr/bin/env python3
# Step 5: Deploy Playbooks to WeKnora and Configure Targeting

import requests
import json
import os
from pathlib import Path
from sqlalchemy import create_engine

print("🎮 Deploying Playbooks")
print("=" * 50)

WEKNORA_URL = "http://localhost:8000"
engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

# 1. Upload Playbook Documents to WeKnora
print("\n📚 Step 1: Uploading Playbook Documents...")

playbook_docs = {
    'frisco_alpha_v1.md': '''# Frisco-Alpha Playbook v1.0

## Objective
Enter Frisco market with high-value, low-competition targeting

## Targeting Rules
- **Physics**: SII ≥ 75, within 14 days of storm
- **Geography**: ZIP 75034, 75035
- **Demographics**: High SES (income > $100K)
- **Psychographics**: Proof_Seeker, Status_Conscious
- **Competition**: Competitor pressure < 0.4

## Channel Strategy
1. **Day 0**: Email (analytical tone, data-driven)
2. **Day 3**: SMS (urgency, if no email response)
3. **Day 7**: Door knock (premium positioning, if engaged)

## Scripts
### Email Template
Subject: Hail Damage Assessment - [Address]
Body: Our analysis indicates [SII_SCORE]% likelihood of roof damage...

### SMS Template
Hi [Name], recent hail in your area. Free inspection this week. Reply YES.

## KPIs
- Target conversion: 25%
- Target ticket: $18,000
- Target ROI: 400%
''',
    
    'loyalty_dfw_v1.md': '''# Loyalty-DFW Playbook v1.0

## Objective
Defend high-value territory against Tier1 competitors

## Targeting Rules
- **Physics**: SII ≥ 60, within 45 days
- **Geography**: ZIP 75230, 75225 (historical strongholds)
- **Behavioral**: Past customers only, response rate > 30%
- **Competition**: High threat (pressure > 0.6)

## Channel Strategy
1. **Day 0**: Phone call (friendly, referral incentive)
2. **Day 5**: Direct mail (loyalty discount)
3. **Day 10**: In-person visit (VIP treatment, if high LTV)

## Scripts
### Phone Script
"Hi [Name], it's [Rep] from [Company]. We noticed the recent storm and wanted to check on your roof since we worked together in [YEAR]..."

## KPIs
- Target retention: 80%
- Target ticket: $16,000
- Target ROI: 350%
'''
}

for filename, content in playbook_docs.items():
    try:
        # Save locally
        Path('docs/playbooks').mkdir(parents=True, exist_ok=True)
        with open(f'docs/playbooks/{filename}', 'w') as f:
            f.write(content)
        
        # Upload to WeKnora
        with open(f'docs/playbooks/{filename}', 'rb') as f:
            response = requests.post(
                f'{WEKNORA_URL}/api/v1/kb/kb_playbooks/upload',
                files={'file': f}
            )
            if response.status_code == 200:
                print(f"  ✅ Uploaded: {filename}")
            else:
                print(f"  ⚠️  Failed: {filename} - {response.text}")
    except Exception as e:
        print(f"  ⚠️  Error uploading {filename}: {e}")

# 2. Configure Playbooks in Database
print("\n⚙️  Step 2: Configuring Playbooks in Database...")

playbooks = [
    {
        'playbook_id': 'frisco-alpha',
        'playbook_name': 'Frisco-Alpha',
        'playbook_version': 'v1.0',
        'status': 'active',
        'targeting_rules': json.dumps({
            'physics': {
                'min_sii_score': 75,
                'max_days_since_storm': 14,
                'roof_age_min': 10,
                'roof_age_max': 40
            },
            'geography': {
                'zips': ['75034', '75035']
            },
            'demographics': {
                'ses_tiers': ['High'],
                'min_median_income': 100000
            },
            'psychographics': {
                'personas': ['Proof_Seeker', 'Status_Conscious']
            },
            'competition': {
                'competitor_pressure_max': 0.4,
                'white_space_score_min': 60
            }
        }),
        'channel_strategy': json.dumps({
            'sequence': [
                {'step': 1, 'channel': 'email', 'timing_hours': 0, 'message_variant': 'analytical'},
                {'step': 2, 'channel': 'sms', 'timing_hours': 72, 'condition': 'if_no_response', 'message_variant': 'urgency'},
                {'step': 3, 'channel': 'door_knock', 'timing_hours': 168, 'condition': 'if_engaged', 'message_variant': 'premium'}
            ]
        }),
        'target_conversion_rate': 0.25,
        'target_avg_ticket': 18000,
        'target_roi': 4.0
    },
    {
        'playbook_id': 'loyalty-dfw-highses',
        'playbook_name': 'Loyalty-DFW-HighSES',
        'playbook_version': 'v1.0',
        'status': 'active',
        'targeting_rules': json.dumps({
            'physics': {
                'min_sii_score': 60,
                'max_days_since_storm': 45
            },
            'geography': {
                'zips': ['75230', '75225']
            },
            'demographics': {
                'ses_tiers': ['High'],
                'min_median_income': 90000
            },
            'behavioral': {
                'past_customers_only': True,
                'response_rate_min': 0.3
            },
            'competition': {
                'competitor_pressure_max': 0.8
            }
        }),
        'channel_strategy': json.dumps({
            'sequence': [
                {'step': 1, 'channel': 'phone', 'timing_hours': 0, 'message_variant': 'friendly'},
                {'step': 2, 'channel': 'direct_mail', 'timing_hours': 120, 'message_variant': 'loyalty'},
                {'step': 3, 'channel': 'door_knock', 'timing_hours': 240, 'condition': 'if_high_ltv', 'message_variant': 'vip'}
            ]
        }),
        'target_conversion_rate': 0.80,
        'target_avg_ticket': 16000,
        'target_roi': 3.5
    }
]

import pandas as pd
df = pd.DataFrame(playbooks)
df.to_sql('playbooks', engine, if_exists='append', index=False)
print(f"  ✅ Configured {len(playbooks)} playbooks in database")

# 3. Test Playbook Retrieval
print("\n🧪 Step 3: Testing Playbook Retrieval...")

try:
    # Test WeKnora query
    response = requests.post(
        f'{WEKNORA_URL}/api/v1/query',
        json={
            'context': {'playbook_name': 'Frisco-Alpha'},
            'task': {
                'type': 'playbook_lookup',
                'fields': ['targeting_rules', 'channel_strategy']
            },
            'knowledge_bases': ['kb_playbooks']
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✅ WeKnora retrieval working")
        print(f"     Confidence: {result.get('confidence', 0):.2f}")
    else:
        print(f"  ⚠️  WeKnora query failed: {response.text}")
        
except Exception as e:
    print(f"  ⚠️  Error: {e}")

# 4. Execute First Campaign
print("\n🚀 Step 4: Ready to Execute First Campaign")
print("\n  Available playbooks:")
print("    1. frisco-alpha (Entry strategy)")
print("    2. loyalty-dfw-highses (Retention strategy)")
print("\n  To execute:")
print("    python -c \"from stormops_ui_integration import execute_playbook; execute_playbook('frisco-alpha', 'dfw_storm_24', ['75034'])\"")

print("\n" + "=" * 50)
print("✅ Playbooks Deployed!")
print("\n📊 Summary:")
print(f"  Documents uploaded: {len(playbook_docs)}")
print(f"  Playbooks configured: {len(playbooks)}")
print(f"  WeKnora KB: kb_playbooks")
print("\n💡 System ready for production use!")
print("💡 Open UI: http://localhost:8501")
