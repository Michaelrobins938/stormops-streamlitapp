
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
    stream.map(lambda x: json.loads(x)) \
          .key_by(lambda x: x['property_id']) \
          .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
          .process(AttributionProcessFunction()) \
          .add_sink(AttributionSink())
    
    env.execute('StormOps Real-Time Attribution')

if __name__ == '__main__':
    process_attribution()
