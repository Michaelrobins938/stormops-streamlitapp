
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
