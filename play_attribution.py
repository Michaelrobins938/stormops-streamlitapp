"""
Play-Level Attribution
Shows which channels carry each play
"""

from sqlalchemy import create_engine, text
import pandas as pd

def calculate_play_attribution(event_id='DFW_STORM_24'):
    """Calculate attribution by play and channel."""
    
    # Read journeys with play info
    engine = create_engine('sqlite:///stormops_journeys.db')
    
    # Load A-tier leads to get play assignments
    leads_df = pd.read_csv('a_tier_leads.csv')
    play_map = dict(zip(leads_df['property_id'], leads_df['recommended_play']))
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT property_id, channel, converted, conversion_value
            FROM customer_journeys
            WHERE event_id = :eid
            ORDER BY property_id, timestamp
        """), {'eid': event_id})
        
        journeys = {}
        for row in result:
            prop_id, channel, converted, value = row
            if prop_id not in journeys:
                journeys[prop_id] = []
            journeys[prop_id].append({
                'channel': channel,
                'converted': converted,
                'value': value
            })
    
    # Calculate play-channel attribution
    play_channel_stats = {}
    
    for prop_id, events in journeys.items():
        play = play_map.get(prop_id, 'Unknown')
        
        if play not in play_channel_stats:
            play_channel_stats[play] = {}
        
        for event in events:
            channel = event['channel']
            if channel not in play_channel_stats[play]:
                play_channel_stats[play][channel] = {'touches': 0, 'conversions': 0, 'value': 0}
            
            play_channel_stats[play][channel]['touches'] += 1
            if event['converted']:
                play_channel_stats[play][channel]['conversions'] += 1
                play_channel_stats[play][channel]['value'] += event['value']
    
    # Calculate credits
    results = []
    for play, channels in play_channel_stats.items():
        total_touches = sum(c['touches'] for c in channels.values())
        for channel, stats in channels.items():
            credit = stats['touches'] / total_touches if total_touches > 0 else 0
            results.append({
                'play': play,
                'channel': channel,
                'credit': credit,
                'touches': stats['touches'],
                'conversions': stats['conversions'],
                'value': stats['value']
            })
    
    return pd.DataFrame(results)


def write_play_attribution_to_db(df, event_id='DFW_STORM_24'):
    """Write play attribution to database."""
    engine = create_engine('sqlite:///stormops_attribution.db')
    
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS play_channel_attribution (
                event_id TEXT,
                play_id TEXT,
                channel TEXT,
                credit FLOAT,
                touches INT,
                conversions INT,
                value FLOAT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (event_id, play_id, channel)
            )
        """))
        
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT OR REPLACE INTO play_channel_attribution 
                (event_id, play_id, channel, credit, touches, conversions, value)
                VALUES (:eid, :play, :channel, :credit, :touches, :conv, :value)
            """), {
                'eid': event_id,
                'play': row['play'],
                'channel': row['channel'],
                'credit': row['credit'],
                'touches': row['touches'],
                'conv': row['conversions'],
                'value': row['value']
            })
    
    print(f"✅ Wrote play attribution: {len(df)} play-channel pairs")


if __name__ == '__main__':
    print("=" * 60)
    print("PLAY-LEVEL ATTRIBUTION")
    print("=" * 60)
    
    df = calculate_play_attribution()
    
    # Show top plays
    print("\nTop Plays by Total Touches:")
    play_totals = df.groupby('play')['touches'].sum().sort_values(ascending=False)
    for play, touches in play_totals.head(5).items():
        print(f"  {play}: {touches} touches")
    
    # Show channel breakdown for top play
    top_play = play_totals.index[0]
    print(f"\nChannel Attribution for {top_play}:")
    play_df = df[df['play'] == top_play].sort_values('credit', ascending=False)
    for _, row in play_df.iterrows():
        print(f"  {row['channel']}: {row['credit']*100:.1f}% ({row['touches']} touches, {row['conversions']} conv)")
    
    # Write to DB
    print("\nWriting to database...")
    write_play_attribution_to_db(df)
    
    print("\n" + "=" * 60)
    print("✅ Play attribution complete")
    print("=" * 60)
