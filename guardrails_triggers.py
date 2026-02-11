"""
Real-Time Guardrails and Triggers
Kafka + Flink → Auto-throttle, escalate, and instant proposals
"""

# Guardrails: Contact frequency, complaints, SLA breaches
GUARDRAILS_FLINK_JOB = """
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment
from datetime import datetime, timedelta

def guardrails_job():
    env = StreamExecutionEnvironment.get_execution_environment()
    t_env = StreamTableEnvironment.create(env)
    
    # Define source: StormOps events from Kafka
    t_env.execute_sql('''
        CREATE TABLE stormops_events (
            property_id STRING,
            event_type STRING,
            channel STRING,
            timestamp TIMESTAMP(3),
            WATERMARK FOR timestamp AS timestamp - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'stormops-events',
            'properties.bootstrap.servers' = 'localhost:9092',
            'format' = 'json'
        )
    ''')
    
    # Guardrail 1: Contact frequency (max 3 touches per 24h)
    t_env.execute_sql('''
        CREATE TABLE contact_violations AS
        SELECT 
            property_id,
            COUNT(*) as touch_count,
            TUMBLE_END(timestamp, INTERVAL '24' HOUR) as window_end
        FROM stormops_events
        WHERE event_type IN ('door_knock', 'sms', 'call', 'email')
        GROUP BY property_id, TUMBLE(timestamp, INTERVAL '24' HOUR)
        HAVING COUNT(*) > 3
    ''')
    
    # Guardrail 2: SLA breaches (response > 24h)
    t_env.execute_sql('''
        CREATE TABLE sla_breaches AS
        SELECT 
            property_id,
            MIN(timestamp) as first_touch,
            MAX(timestamp) as last_response,
            TIMESTAMPDIFF(HOUR, MIN(timestamp), MAX(timestamp)) as response_hours
        FROM stormops_events
        WHERE event_type IN ('door_knock', 'call_response', 'proposal_sent')
        GROUP BY property_id, TUMBLE(timestamp, INTERVAL '48' HOUR)
        HAVING TIMESTAMPDIFF(HOUR, MIN(timestamp), MAX(timestamp)) > 24
    ''')
    
    # Guardrail 3: Complaints (auto-throttle)
    t_env.execute_sql('''
        CREATE TABLE complaint_throttles AS
        SELECT 
            property_id,
            'THROTTLE' as action,
            timestamp
        FROM stormops_events
        WHERE event_type = 'complaint'
    ''')
    
    # Write violations to action queue
    t_env.execute_sql('''
        CREATE TABLE action_queue (
            property_id STRING,
            action STRING,
            reason STRING,
            timestamp TIMESTAMP(3)
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'stormops-actions',
            'properties.bootstrap.servers' = 'localhost:9092',
            'format' = 'json'
        )
    ''')
    
    # Insert violations
    t_env.execute_sql('''
        INSERT INTO action_queue
        SELECT property_id, 'THROTTLE', 'contact_frequency', window_end
        FROM contact_violations
    ''')
    
    env.execute('StormOps Guardrails')

if __name__ == '__main__':
    guardrails_job()
"""

# Triggers: GA4 high-intent, hail alerts, competitor moves
TRIGGERS_FLINK_JOB = """
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment

def triggers_job():
    env = StreamExecutionEnvironment.get_execution_environment()
    t_env = StreamTableEnvironment.create(env)
    
    # GA4 events source
    t_env.execute_sql('''
        CREATE TABLE ga4_events (
            user_id STRING,
            event_name STRING,
            property_id STRING,
            timestamp TIMESTAMP(3),
            WATERMARK FOR timestamp AS timestamp - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'ga4-events',
            'properties.bootstrap.servers' = 'localhost:9092',
            'format' = 'json'
        )
    ''')
    
    # Trigger 1: High-intent GA4 events → Instant proposal
    t_env.execute_sql('''
        CREATE TABLE high_intent_triggers AS
        SELECT 
            property_id,
            'CREATE_PROPOSAL' as action,
            'high_intent_ga4' as trigger_type,
            timestamp
        FROM ga4_events
        WHERE event_name IN ('estimate_tool_used', 'quote_started', 'call_click')
    ''')
    
    # Trigger 2: Hail alerts → Instant outreach
    t_env.execute_sql('''
        CREATE TABLE weather_events (
            zip_code STRING,
            event_type STRING,
            severity DOUBLE,
            timestamp TIMESTAMP(3),
            WATERMARK FOR timestamp AS timestamp - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'weather-alerts',
            'properties.bootstrap.servers' = 'localhost:9092',
            'format' = 'json'
        )
    ''')
    
    t_env.execute_sql('''
        CREATE TABLE hail_triggers AS
        SELECT 
            zip_code,
            'ACTIVATE_STORM_PLAY' as action,
            'hail_alert' as trigger_type,
            severity,
            timestamp
        FROM weather_events
        WHERE event_type = 'hail' AND severity > 1.5
    ''')
    
    # Trigger 3: Competitor moves → Adjust pricing
    t_env.execute_sql('''
        CREATE TABLE competitor_events (
            zip_code STRING,
            competitor STRING,
            action STRING,
            timestamp TIMESTAMP(3),
            WATERMARK FOR timestamp AS timestamp - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'competitor-intel',
            'properties.bootstrap.servers' = 'localhost:9092',
            'format' = 'json'
        )
    ''')
    
    t_env.execute_sql('''
        CREATE TABLE competitor_triggers AS
        SELECT 
            zip_code,
            'ADJUST_PRICING' as action,
            'competitor_move' as trigger_type,
            competitor,
            timestamp
        FROM competitor_events
        WHERE action IN ('price_drop', 'promotion_launch')
    ''')
    
    # Unified action queue
    t_env.execute_sql('''
        CREATE TABLE action_queue (
            entity_id STRING,
            action STRING,
            trigger_type STRING,
            metadata STRING,
            timestamp TIMESTAMP(3)
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'stormops-actions',
            'properties.bootstrap.servers' = 'localhost:9092',
            'format' = 'json'
        )
    ''')
    
    env.execute('StormOps Triggers')

if __name__ == '__main__':
    triggers_job()
"""

# Action consumer: Reads from action queue and executes
ACTION_CONSUMER = """
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
"""

if __name__ == '__main__':
    print("=" * 60)
    print("REAL-TIME GUARDRAILS & TRIGGERS SETUP")
    print("=" * 60)
    
    # Write Flink jobs
    with open('flink_guardrails_job.py', 'w') as f:
        f.write(GUARDRAILS_FLINK_JOB)
    print("✅ Created flink_guardrails_job.py")
    
    with open('flink_triggers_job.py', 'w') as f:
        f.write(TRIGGERS_FLINK_JOB)
    print("✅ Created flink_triggers_job.py")
    
    with open('action_consumer.py', 'w') as f:
        f.write(ACTION_CONSUMER)
    print("✅ Created action_consumer.py")
    
    print("\n" + "=" * 60)
    print("To start guardrails & triggers:")
    print("  1. docker-compose up -d  # Start Kafka + Flink")
    print("  2. python flink_guardrails_job.py")
    print("  3. python flink_triggers_job.py")
    print("  4. python action_consumer.py")
    print("=" * 60)
