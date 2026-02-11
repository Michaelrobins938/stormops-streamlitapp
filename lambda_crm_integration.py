"""
Lambda handler for CRM integration (AWS deployment)
"""

import json
import os
import psycopg2
from crm_integration import MockCRMIntegration
from datetime import datetime

DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')


def lambda_handler(event, context):
    """
    Lambda handler: pushes leads, routes to CRM.
    Triggered on demand via API Gateway.
    """
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        action = body.get('action')  # create_lead, push_route, send_sms
        event_id = body.get('event_id')
        
        if not action or not event_id:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing action or event_id')
            }
        
        crm = MockCRMIntegration()
        
        if action == 'create_lead':
            lead_id = crm.create_lead(
                first_name=body.get('first_name', 'John'),
                last_name=body.get('last_name', 'Doe'),
                phone=body.get('phone', '555-0000'),
                email=body.get('email', 'john@example.com'),
                address=body.get('address', '123 Main St'),
                zip_code=body.get('zip_code', '75034'),
                sii_score=body.get('sii_score', 75),
                hail_intensity_mm=body.get('hail_intensity_mm', 50),
                event_id=event_id,
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'lead_id': lead_id,
                    'action': action,
                    'timestamp': datetime.now().isoformat(),
                })
            }
        
        elif action == 'send_sms':
            success = crm.send_sms(
                phone=body.get('phone'),
                message=body.get('message'),
            )
            
            return {
                'statusCode': 200 if success else 500,
                'body': json.dumps({
                    'success': success,
                    'action': action,
                    'timestamp': datetime.now().isoformat(),
                })
            }
        
        elif action == 'push_route':
            success = crm.push_route(
                route_id=body.get('route_id'),
                rep_id=body.get('rep_id'),
                route_data=body.get('route_data', {}),
            )
            
            return {
                'statusCode': 200 if success else 500,
                'body': json.dumps({
                    'success': success,
                    'action': action,
                    'timestamp': datetime.now().isoformat(),
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps(f'Unknown action: {action}')
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
