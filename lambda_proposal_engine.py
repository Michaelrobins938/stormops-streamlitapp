"""
Lambda handler for proposal engine (AWS deployment)
"""

import json
import os
from proposal_engine import ProposalEngine
from datetime import datetime

DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')


def lambda_handler(event, context):
    """
    Lambda handler: generates Proposals (lead gen, route build, SMS).
    Triggered on demand via API Gateway.
    """
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        event_id = body.get('event_id')
        zip_code = body.get('zip_code', '75034')
        proposal_type = body.get('proposal_type')  # lead_gen, route_build, sms_campaign
        
        if not event_id or not proposal_type:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing event_id or proposal_type')
            }
        
        engine = ProposalEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        engine.connect()
        
        proposal_id = None
        
        if proposal_type == 'lead_gen':
            proposal_id = engine.generate_lead_gen_proposal(
                event_id=event_id,
                zip_code=zip_code,
                sii_min=60,
            )
        elif proposal_type == 'route_build':
            proposal_id = engine.generate_route_build_proposal(
                event_id=event_id,
                zip_code=zip_code,
                sii_min=70,
                num_canvassers=4,
            )
        elif proposal_type == 'sms_campaign':
            proposal_id = engine.generate_sms_campaign_proposal(
                event_id=event_id,
                zip_code=zip_code,
            )
        
        engine.close()
        
        if not proposal_id:
            return {
                'statusCode': 500,
                'body': json.dumps('Failed to generate proposal')
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'proposal_id': proposal_id,
                'proposal_type': proposal_type,
                'event_id': event_id,
                'zip_code': zip_code,
                'timestamp': datetime.now().isoformat(),
            })
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
