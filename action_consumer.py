
from kafka import KafkaConsumer
import json
from sqlalchemy import create_engine, text
from datetime import datetime

def consume_actions():
    consumer = KafkaConsumer(
        'stormops-actions',
        bootstrap_servers=['localhost:9092'],
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    engine = create_engine('sqlite:///stormops_attribution.db')
    
    print("Listening for actions...")
    
    for message in consumer:
        action = message.value
        
        print(f"Action received: {action}")
        
        # Execute action
        if action['action'] == 'THROTTLE':
            throttle_property(engine, action['property_id'], action['reason'])
        
        elif action['action'] == 'CREATE_PROPOSAL':
            create_instant_proposal(engine, action['property_id'], action['trigger_type'])
        
        elif action['action'] == 'ACTIVATE_STORM_PLAY':
            activate_storm_play(engine, action['zip_code'], action['severity'])
        
        elif action['action'] == 'ADJUST_PRICING':
            adjust_pricing(engine, action['zip_code'], action['competitor'])

def throttle_property(engine, property_id, reason):
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT OR REPLACE INTO property_throttles 
            (property_id, reason, throttled_until)
            VALUES (:pid, :reason, datetime('now', '+7 days'))
        '''), {'pid': property_id, 'reason': reason})
    print(f"✅ Throttled {property_id}: {reason}")

def create_instant_proposal(engine, property_id, trigger):
    # Get next best action from uplift model
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT next_best_action, expected_uplift
            FROM lead_uplift
            WHERE property_id = :pid
        '''), {'pid': property_id}).fetchone()
    
    if result:
        action, uplift = result
        print(f"✅ Creating proposal for {property_id}: {action} (uplift: {uplift:.3f})")
        # Create proposal in CRM/proposal system

def activate_storm_play(engine, zip_code, severity):
    print(f"✅ Activating storm play for {zip_code} (severity: {severity})")
    # Trigger storm playbook for ZIP

def adjust_pricing(engine, zip_code, competitor):
    print(f"✅ Adjusting pricing in {zip_code} (competitor: {competitor})")
    # Update pricing rules

if __name__ == '__main__':
    consume_actions()
