"""
StormOps UI Integration Layer
Connects control plane UI to SII ML pipeline, GA4 integration, and Strategic Plays
"""

import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import uuid

# Database connection
engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

def generate_leads_physics_driven(
    zip_code: str,
    min_sii_score: float,
    event_id: str,
    playbook_id: str = "frisco-alpha"
) -> dict:
    """
    Generate leads using SII scores + GA4 intent + Strategic Play logic.
    
    This is what happens when user clicks "Generate Leads now" in the UI.
    """
    
    # 1. Query properties with SII scores above threshold
    query = text("""
        SELECT 
            p.property_id,
            p.address,
            p.latitude,
            p.longitude,
            pe.sii_score,
            pe.moe_usd,
            r.roof_age_years,
            r.roof_material,
            pp.primary_persona,
            pp.preferred_channel,
            ct.median_household_income,
            tm.contractor_density,
            
            -- GA4 high-intent signals (last 30 days)
            COUNT(DISTINCT wbe.event_name) FILTER (
                WHERE wbe.event_name IN ('estimate_tool_used', 'quote_started', 'call_click')
            ) as high_intent_events,
            MAX(wbe.event_timestamp) as last_web_activity,
            
            -- Governance checks
            pgov.has_sms_consent,
            pgov.has_phone_consent,
            pgov.next_eligible_contact,
            pgov.in_exclusion_zone
            
        FROM properties p
        JOIN property_exposure pe ON p.property_id = pe.property_id
        JOIN roofs r ON p.property_id = r.property_id
        LEFT JOIN psychographic_profiles pp ON p.property_id = pp.property_id
        JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
        JOIN tract_metrics tm ON ct.tract_geoid = tm.tract_geoid
        LEFT JOIN web_behavior_events wbe ON p.property_id = wbe.property_id
            AND wbe.event_timestamp > NOW() - INTERVAL '30 days'
        LEFT JOIN properties_with_governance pgov ON p.property_id = pgov.property_id
        
        WHERE p.zip_code = :zip_code
          AND pe.sii_score >= :min_sii_score
          AND pe.event_id = :event_id
          AND pgov.in_exclusion_zone = FALSE
          AND pgov.next_eligible_contact <= NOW()
        
        GROUP BY p.property_id, p.address, p.latitude, p.longitude,
                 pe.sii_score, pe.moe_usd, r.roof_age_years, r.roof_material,
                 pp.primary_persona, pp.preferred_channel, ct.median_household_income,
                 tm.contractor_density, pgov.has_sms_consent, pgov.has_phone_consent,
                 pgov.next_eligible_contact, pgov.in_exclusion_zone
        
        ORDER BY pe.sii_score DESC, high_intent_events DESC
        LIMIT 500
    """)
    
    with engine.connect() as conn:
        leads_df = pd.read_sql(query, conn, params={
            'zip_code': zip_code,
            'min_sii_score': min_sii_score,
            'event_id': event_id
        })
    
    # 2. Tier leads by SII + GA4 intent
    leads_df['tier'] = leads_df.apply(lambda row: 
        'A' if row['sii_score'] >= 80 and row['high_intent_events'] > 0 else
        'B' if row['sii_score'] >= 70 else
        'C', axis=1
    )
    
    # 3. Create proposals for each lead
    proposals = []
    for _, lead in leads_df.iterrows():
        proposal_id = str(uuid.uuid4())
        
        # Determine channel based on persona + consent
        if lead['preferred_channel'] == 'sms' and lead['has_sms_consent']:
            channel = 'sms'
        elif lead['preferred_channel'] == 'phone' and lead['has_phone_consent']:
            channel = 'phone'
        else:
            channel = 'door_knock'
        
        proposal = {
            'proposal_id': proposal_id,
            'property_id': lead['property_id'],
            'playbook_id': playbook_id,
            'event_id': event_id,
            'tier': lead['tier'],
            'sii_score': lead['sii_score'],
            'moe_usd': lead['moe_usd'],
            'channel': channel,
            'persona': lead['primary_persona'],
            'high_intent_events': lead['high_intent_events'],
            'priority': 1 if lead['tier'] == 'A' else 2 if lead['tier'] == 'B' else 3,
            'status': 'pending',
            'created_at': datetime.now()
        }
        proposals.append(proposal)
    
    # 4. Insert proposals into database
    proposals_df = pd.DataFrame(proposals)
    with engine.connect() as conn:
        proposals_df.to_sql('proposals', conn, if_exists='append', index=False)
        conn.commit()
    
    # 5. Generate summary stats
    summary = {
        'total_leads': len(leads_df),
        'tier_a': len(leads_df[leads_df['tier'] == 'A']),
        'tier_b': len(leads_df[leads_df['tier'] == 'B']),
        'tier_c': len(leads_df[leads_df['tier'] == 'C']),
        'avg_sii_score': leads_df['sii_score'].mean(),
        'total_moe': leads_df['moe_usd'].sum(),
        'high_intent_count': len(leads_df[leads_df['high_intent_events'] > 0]),
        'proposals_created': len(proposals),
        'playbook_id': playbook_id,
        'event_id': event_id,
        'zip_code': zip_code
    }
    
    return summary


def execute_playbook(playbook_id: str, event_id: str, zip_codes: list) -> dict:
    """
    Execute a full strategic playbook (e.g., Frisco-Alpha).
    
    This orchestrates:
    - Lead generation with SII filtering
    - GA4 intent scoring
    - Proposal creation
    - Route optimization
    - Attribution tagging
    """
    
    # 1. Load playbook configuration
    with engine.connect() as conn:
        playbook = pd.read_sql(
            "SELECT * FROM playbooks WHERE playbook_id = :playbook_id",
            conn,
            params={'playbook_id': playbook_id}
        ).iloc[0]
    
    # 2. Generate leads for each ZIP
    all_leads = []
    for zip_code in zip_codes:
        leads = generate_leads_physics_driven(
            zip_code=zip_code,
            min_sii_score=playbook['targeting_rules']['physics']['min_sii_score'],
            event_id=event_id,
            playbook_id=playbook_id
        )
        all_leads.append(leads)
    
    # 3. Create playbook execution record
    execution_id = str(uuid.uuid4())
    execution = {
        'execution_id': execution_id,
        'playbook_id': playbook_id,
        'triggered_by_event_id': event_id,
        'execution_start': datetime.now(),
        'status': 'running',
        'properties_targeted': sum(l['total_leads'] for l in all_leads),
        'properties_contacted': 0,
        'properties_converted': 0
    }
    
    with engine.connect() as conn:
        pd.DataFrame([execution]).to_sql('playbook_executions', conn, if_exists='append', index=False)
        conn.commit()
    
    # 4. Tag all proposals with execution_id for attribution
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE proposals
            SET execution_id = :execution_id,
                ga_campaign_tag = :campaign_tag
            WHERE playbook_id = :playbook_id
              AND created_at > NOW() - INTERVAL '5 minutes'
        """), {
            'execution_id': execution_id,
            'campaign_tag': f"{playbook_id}_{event_id}",
            'playbook_id': playbook_id
        })
        conn.commit()
    
    return {
        'execution_id': execution_id,
        'playbook_id': playbook_id,
        'total_leads': sum(l['total_leads'] for l in all_leads),
        'tier_a_leads': sum(l['tier_a'] for l in all_leads),
        'high_intent_leads': sum(l['high_intent_count'] for l in all_leads),
        'total_moe': sum(l['total_moe'] for l in all_leads),
        'zip_codes': zip_codes,
        'status': 'running'
    }


def get_ui_dashboard_data(event_id: str) -> dict:
    """
    Get current dashboard state for UI display.
    
    This powers the metrics shown in the control plane.
    """
    
    with engine.connect() as conn:
        # Storm event details
        event = pd.read_sql(
            "SELECT * FROM storm_events WHERE event_id = :event_id",
            conn,
            params={'event_id': event_id}
        ).iloc[0]
        
        # Impacted properties with SII scores
        impacted = pd.read_sql(text("""
            SELECT 
                COUNT(*) as total_properties,
                COUNT(*) FILTER (WHERE sii_score >= 80) as high_sii_count,
                COUNT(*) FILTER (WHERE sii_score >= 60) as medium_sii_count,
                AVG(sii_score) as avg_sii,
                SUM(moe_usd) as total_moe
            FROM property_exposure
            WHERE event_id = :event_id
        """), conn, params={'event_id': event_id}).iloc[0]
        
        # Active proposals
        proposals = pd.read_sql(text("""
            SELECT 
                COUNT(*) as total_proposals,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE tier = 'A') as tier_a_count
            FROM proposals
            WHERE event_id = :event_id
        """), conn, params={'event_id': event_id}).iloc[0]
        
        # GA4 high-intent signals
        web_intent = pd.read_sql(text("""
            SELECT 
                COUNT(DISTINCT property_id) as properties_with_intent,
                COUNT(*) as total_intent_events
            FROM web_behavior_events
            WHERE storm_event_id = :event_id
              AND event_name IN ('estimate_tool_used', 'quote_started', 'call_click')
              AND event_timestamp > NOW() - INTERVAL '7 days'
        """), conn, params={'event_id': event_id}).iloc[0]
    
    return {
        'event': {
            'event_id': event_id,
            'magnitude': event['magnitude'],
            'begin_datetime': event['begin_datetime'],
            'county': event['county']
        },
        'impact': {
            'total_properties': int(impacted['total_properties']),
            'high_sii_count': int(impacted['high_sii_count']),
            'medium_sii_count': int(impacted['medium_sii_count']),
            'avg_sii': float(impacted['avg_sii']),
            'total_moe': int(impacted['total_moe'])
        },
        'proposals': {
            'total': int(proposals['total_proposals']),
            'pending': int(proposals['pending']),
            'in_progress': int(proposals['in_progress']),
            'completed': int(proposals['completed']),
            'tier_a': int(proposals['tier_a_count'])
        },
        'web_intent': {
            'properties_with_intent': int(web_intent['properties_with_intent']),
            'total_events': int(web_intent['total_intent_events'])
        }
    }


def update_storm_play_score(event_id: str) -> float:
    """
    Calculate Storm Play Score based on SII, GA4 intent, and market conditions.
    
    This is the 0-100 score shown in the UI.
    """
    
    dashboard = get_ui_dashboard_data(event_id)
    
    # Score components (0-100 scale)
    physics_score = min(100, dashboard['impact']['avg_sii'])
    
    intent_score = min(100, 
        (dashboard['web_intent']['properties_with_intent'] / 
         max(1, dashboard['impact']['total_properties'])) * 200
    )
    
    coverage_score = min(100,
        (dashboard['proposals']['total'] / 
         max(1, dashboard['impact']['high_sii_count'])) * 100
    )
    
    # Weighted average
    play_score = (
        physics_score * 0.5 +
        intent_score * 0.3 +
        coverage_score * 0.2
    )
    
    # Update in database
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE storm_events
            SET play_score = :play_score,
                updated_at = NOW()
            WHERE event_id = :event_id
        """), {'play_score': play_score, 'event_id': event_id})
        conn.commit()
    
    return play_score


# Example usage for UI button handlers
if __name__ == "__main__":
    # Simulate "Generate Leads now" button click
    result = generate_leads_physics_driven(
        zip_code="75034",
        min_sii_score=70.0,
        event_id="dfw_storm_24",
        playbook_id="frisco-alpha"
    )
    
    print(f"Generated {result['total_leads']} leads:")
    print(f"  Tier A (SII 80+, high intent): {result['tier_a']}")
    print(f"  Tier B (SII 70-79): {result['tier_b']}")
    print(f"  Tier C (SII 60-69): {result['tier_c']}")
    print(f"  High-intent web visitors: {result['high_intent_count']}")
    print(f"  Total MOE: ${result['total_moe']:,}")
    print(f"  Proposals created: {result['proposals_created']}")
    
    # Execute full playbook
    execution = execute_playbook(
        playbook_id="frisco-alpha",
        event_id="dfw_storm_24",
        zip_codes=["75034", "75035"]
    )
    
    print(f"\nPlaybook execution {execution['execution_id']}:")
    print(f"  Total leads: {execution['total_leads']}")
    print(f"  Tier A: {execution['tier_a_leads']}")
    print(f"  High-intent: {execution['high_intent_leads']}")
    
    # Update dashboard
    dashboard = get_ui_dashboard_data("dfw_storm_24")
    play_score = update_storm_play_score("dfw_storm_24")
    
    print(f"\nDashboard updated:")
    print(f"  Storm Play Score: {play_score:.1f}/100")
    print(f"  Impacted properties: {dashboard['impact']['total_properties']}")
    print(f"  Active proposals: {dashboard['proposals']['total']}")
