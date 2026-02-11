"""
Real-Time Streaming Attribution
Kafka → Flink → Attribution (Minimal Setup)
"""

# Kafka producer for StormOps events
def publish_event_to_kafka(event: dict):
    """Publish StormOps event to Kafka topic."""
    try:
        from kafka import KafkaProducer
        import json
        
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        producer.send('stormops-events', event)
        producer.flush()
        return True
    except Exception as e:
        print(f"Kafka publish failed: {e}")
        return False


# Flink job (Python API)
FLINK_JOB = """
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors import FlinkKafkaConsumer
from pyflink.common.serialization import SimpleStringSchema
import json

def process_attribution():
    env = StreamExecutionEnvironment.get_execution_environment()
    
    # Kafka source
    kafka_consumer = FlinkKafkaConsumer(
        topics='stormops-events',
        deserialization_schema=SimpleStringSchema(),
        properties={'bootstrap.servers': 'localhost:9092', 'group.id': 'attribution'}
    )
    
    # Process stream
    stream = env.add_source(kafka_consumer)
    
    # Window by property_id and calculate attribution every 5 minutes
    stream.map(lambda x: json.loads(x)) \\
          .key_by(lambda x: x['property_id']) \\
          .window(TumblingEventTimeWindows.of(Time.minutes(5))) \\
          .process(AttributionProcessFunction()) \\
          .add_sink(AttributionSink())
    
    env.execute('StormOps Real-Time Attribution')

if __name__ == '__main__':
    process_attribution()
"""


# WebSocket server for live UI updates
WEBSOCKET_SERVER = """
import asyncio
import websockets
import json
from sqlalchemy import create_engine, text

async def attribution_updates(websocket, path):
    engine = create_engine('sqlite:///stormops_attribution.db')
    
    while True:
        # Query latest attribution
        with engine.connect() as conn:
            result = conn.execute(text('''
                SELECT channel, credit, conversions, timestamp
                FROM channel_attribution
                WHERE event_id = 'DFW_STORM_24'
                ORDER BY timestamp DESC
                LIMIT 10
            '''))
            
            data = [dict(row._mapping) for row in result]
        
        # Send to client
        await websocket.send(json.dumps({
            'type': 'attribution_update',
            'data': data,
            'timestamp': str(datetime.now())
        }))
        
        await asyncio.sleep(5)  # Update every 5 seconds

async def main():
    async with websockets.serve(attribution_updates, 'localhost', 8765):
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())
"""


# Docker Compose for full stack
DOCKER_COMPOSE = """
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"

  flink-jobmanager:
    image: flink:latest
    command: jobmanager
    environment:
      - JOB_MANAGER_RPC_ADDRESS=flink-jobmanager
    ports:
      - "8081:8081"

  flink-taskmanager:
    image: flink:latest
    depends_on:
      - flink-jobmanager
    command: taskmanager
    environment:
      - JOB_MANAGER_RPC_ADDRESS=flink-jobmanager

  trino:
    image: trinodb/trino:latest
    ports:
      - "8080:8080"

  postgres:
    image: postgres:latest
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: stormops
    ports:
      - "5432:5432"
"""


if __name__ == '__main__':
    print("=" * 60)
    print("REAL-TIME STREAMING SETUP")
    print("=" * 60)
    
    # Write files
    with open('flink_attribution_job.py', 'w') as f:
        f.write(FLINK_JOB)
    print("✅ Created flink_attribution_job.py")
    
    with open('websocket_server.py', 'w') as f:
        f.write(WEBSOCKET_SERVER)
    print("✅ Created websocket_server.py")
    
    with open('docker-compose.yml', 'w') as f:
        f.write(DOCKER_COMPOSE)
    print("✅ Created docker-compose.yml")
    
    print("\n" + "=" * 60)
    print("To start streaming stack:")
    print("  docker-compose up -d")
    print("\nTo run Flink job:")
    print("  python flink_attribution_job.py")
    print("\nTo start WebSocket server:")
    print("  python websocket_server.py")
    print("=" * 60)
