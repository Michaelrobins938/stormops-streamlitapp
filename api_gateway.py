"""
API Gateway routes for StormOps
"""

from flask import Flask, request, jsonify
from datetime import datetime
import uuid

from proposal_engine import ProposalEngine
from route_optimizer import RouteOptimizer
from crm_integration import MockCRMIntegration
from moe import MarkovOpportunityEngine
from sla_monitor import SLAMonitor
from forecast_monitor import ForecastMonitor
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


@app.route('/events', methods=['GET'])
def list_events():
    import psycopg2
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, peak_hail_inches, max_wind_mph, estimated_value_usd, status
            FROM events ORDER BY event_date DESC LIMIT 10
        """)
        events = [{'id': r[0], 'name': r[1], 'hail': r[2], 'wind': r[3], 'value': r[4], 'status': r[5]} 
                  for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proposals', methods=['POST'])
def create_proposal():
    data = request.json
    event_id = data.get('event_id')
    proposal_type = data.get('type')
    zip_code = data.get('zip_code', '75034')
    
    try:
        engine = ProposalEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        engine.connect()
        
        if proposal_type == 'lead_gen':
            proposal_id = engine.generate_lead_gen_proposal(event_id, zip_code)
        elif proposal_type == 'route_build':
            proposal_id = engine.generate_route_build_proposal(event_id, zip_code)
        elif proposal_type == 'sms_campaign':
            proposal_id = engine.generate_sms_campaign_proposal(event_id, zip_code)
        else:
            return jsonify({'error': 'Unknown proposal type'}), 400
        
        engine.close()
        return jsonify({'proposal_id': proposal_id, 'type': proposal_type})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proposals/<proposal_id>/approve', methods=['POST'])
def approve_proposal(proposal_id):
    try:
        engine = ProposalEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        engine.connect()
        engine.approve_proposal(proposal_id)
        engine.close()
        return jsonify({'status': 'approved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/routes', methods=['POST'])
def build_routes():
    data = request.json
    event_id = data.get('event_id')
    zip_code = data.get('zip_code', '75034')
    
    try:
        optimizer = RouteOptimizer(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        optimizer.connect()
        route_ids = optimizer.build_routes(event_id, zip_code)
        optimizer.close()
        return jsonify({'route_ids': route_ids, 'count': len(route_ids)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/metrics/<event_id>', methods=['GET'])
def get_metrics(event_id):
    try:
        monitor = SLAMonitor(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        monitor.connect()
        metrics = monitor.get_dashboard_metrics(event_id)
        monitor.close()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/operational-score/<event_id>', methods=['GET'])
def get_op_score(event_id):
    try:
        moe = MarkovOpportunityEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
        moe.connect()
        score = moe.get_operational_score(event_id)
        moe.close()
        return jsonify({'operational_score': score})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/forecast-alerts', methods=['POST'])
def check_forecast():
    data = request.json
    event_id = data.get('event_id')
    forecast_data = data.get('forecast')
    
    try:
        fm = ForecastMonitor()
        alerts = fm.check_forecast_alerts(event_id, forecast_data)
        return jsonify({'alerts': alerts, 'count': len(alerts)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/crm/lead', methods=['POST'])
def create_crm_lead():
    data = request.json
    
    try:
        crm = MockCRMIntegration()
        lead_id = crm.create_lead(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            phone=data.get('phone'),
            email=data.get('email'),
            address=data.get('address'),
            zip_code=data.get('zip_code'),
            sii_score=data.get('sii_score'),
            hail_intensity_mm=data.get('hail_intensity_mm'),
            event_id=data.get('event_id'),
        )
        return jsonify({'lead_id': lead_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/crm/sms', methods=['POST'])
def send_sms():
    data = request.json
    
    try:
        crm = MockCRMIntegration()
        success = crm.send_sms(data.get('phone'), data.get('message'))
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
