"""
Webhook handlers for CRM events (ServiceTitan/JobNimbus)
"""

from flask import Flask, request, jsonify
import psycopg2
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

app = Flask(__name__)


@app.route('/webhooks/lead-contacted', methods=['POST'])
def lead_contacted():
    """Handle lead contact event from CRM"""
    data = request.json
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Update lead status
        cursor.execute("""
            UPDATE leads
            SET lead_status = 'contacted', updated_at = NOW()
            WHERE crm_lead_id = %s
        """, (data.get('crm_lead_id'),))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/webhooks/inspection-completed', methods=['POST'])
def inspection_completed():
    """Handle inspection completion event"""
    data = request.json
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Update lead status
        cursor.execute("""
            UPDATE leads
            SET lead_status = 'inspected', updated_at = NOW()
            WHERE crm_lead_id = %s
        """, (data.get('crm_lead_id'),))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/webhooks/job-created', methods=['POST'])
def job_created():
    """Handle job creation event"""
    data = request.json
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Update lead status
        cursor.execute("""
            UPDATE leads
            SET lead_status = 'closed', updated_at = NOW()
            WHERE crm_lead_id = %s
        """, (data.get('crm_lead_id'),))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/webhooks/route-started', methods=['POST'])
def route_started():
    """Handle route start event"""
    data = request.json
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Update route status
        cursor.execute("""
            UPDATE routes
            SET status = 'active', updated_at = NOW()
            WHERE id = %s
        """, (data.get('route_id'),))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/webhooks/route-completed', methods=['POST'])
def route_completed():
    """Handle route completion event"""
    data = request.json
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Update route status
        cursor.execute("""
            UPDATE routes
            SET status = 'completed', updated_at = NOW()
            WHERE id = %s
        """, (data.get('route_id'),))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
