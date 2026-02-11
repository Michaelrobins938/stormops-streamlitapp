
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
