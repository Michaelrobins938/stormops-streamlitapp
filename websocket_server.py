
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
