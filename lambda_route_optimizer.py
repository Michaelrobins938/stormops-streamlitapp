"""
Lambda handler for route optimizer (AWS deployment)
"""

import json
import os
from route_optimizer import RouteOptimizer
from datetime import datetime

DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')


def lambda_handler(event, context):
    """
    Lambda handler: builds optimized routes.
    Triggered on demand via API Gateway.
    """
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        event_id = body.get('event_id')
        zip_code = body.get('zip_code', '75034')
        sii_min = body.get('sii_min', 70)
        num_canvassers = body.get('num_canvassers', 4)
        
        if not event_id:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing event_id')
            }
        
        optimizer = RouteOptimizer(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        optimizer.connect()
        
        route_ids = optimizer.build_routes(
            event_id=event_id,
            zip_code=zip_code,
            sii_min=sii_min,
            num_canvassers=num_canvassers,
        )
        
        optimizer.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'route_ids': route_ids,
                'route_count': len(route_ids),
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
