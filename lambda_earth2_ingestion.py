"""
Lambda handler for Earth-2 ingestion (AWS deployment)
"""

import json
import os
from earth2_ingestion import Earth2Ingestion
from datetime import datetime
import numpy as np

DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')


def lambda_handler(event, context):
    """
    Lambda handler: pulls Earth-2 hail fields, ingests to database.
    Triggered every 15 minutes.
    """
    
    try:
        ingestion = Earth2Ingestion(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        ingestion.connect()
        
        # Mock hail field (replace with real Earth-2 API call)
        hail_field = np.random.uniform(0, 70, size=(100, 100))
        grid_bounds = (32.5, 33.5, -97.5, -96.5)
        
        # Get active event
        import psycopg2
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM events WHERE status = 'active' LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            return {
                'statusCode': 404,
                'body': json.dumps('No active events')
            }
        
        event_id = result[0]
        
        # Ingest
        count = ingestion.ingest_hail_field(
            event_id=event_id,
            hail_field=hail_field,
            grid_bounds=grid_bounds,
            timestamp=datetime.now(),
        )
        
        # Update SII
        sii_count = ingestion.update_impact_scores_with_sii(event_id)
        
        ingestion.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'event_id': event_id,
                'impact_scores_ingested': count,
                'sii_scores_updated': sii_count,
                'timestamp': datetime.now().isoformat(),
            })
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
