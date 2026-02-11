"""
StormOps Attribution UI Display
Minimal function to show attribution in Streamlit UI
"""

import pandas as pd
from sqlalchemy import create_engine, text

def get_control_results(event_id: str = 'DFW_STORM_24') -> list:
    """Query control group experiment results."""
    engine = create_engine('sqlite:///stormops_attribution.db')
    
    try:
        with engine.connect() as conn:
            experiments = pd.read_sql(text("""
                SELECT experiment_id, name, play_id
                FROM experiments
                WHERE status = 'active'
            """), conn)
            
            if experiments.empty:
                return []
            
            results = []
            for _, exp in experiments.iterrows():
                # Get assignments
                assignments = pd.read_sql(text("""
                    SELECT property_id, variant
                    FROM experiment_assignments
                    WHERE experiment_id = :eid
                """), conn, params={'eid': exp['experiment_id']})
                
                # Get conversions
                engine_journeys = create_engine('sqlite:///stormops_journeys.db')
                with engine_journeys.connect() as jconn:
                    conversions = pd.read_sql(text("""
                        SELECT property_id, MAX(CAST(converted AS INTEGER)) as converted
                        FROM customer_journeys
                        GROUP BY property_id
                    """), jconn)
                
                # Merge
                data = assignments.merge(conversions, on='property_id', how='left')
                data['converted'] = data['converted'].fillna(0)
                
                # Calculate metrics
                treatment = data[data['variant'] == 'treatment']
                control = data[data['variant'] == 'control']
                
                treatment_rate = treatment['converted'].mean() if len(treatment) > 0 else 0
                control_rate = control['converted'].mean() if len(control) > 0 else 0
                uplift = treatment_rate - control_rate
                
                results.append({
                    'experiment_id': exp['experiment_id'],
                    'name': exp['name'],
                    'play_id': exp['play_id'],
                    'treatment_n': len(treatment),
                    'control_n': len(control),
                    'treatment_rate': treatment_rate,
                    'control_rate': control_rate,
                    'uplift': uplift,
                    'uplift_pct': (uplift / control_rate * 100) if control_rate > 0 else 0
                })
            
            return results
    except:
        return []


def get_play_attribution(event_id: str = 'DFW_STORM_24') -> pd.DataFrame:
    """Query play attribution data for display in UI."""
    engine = create_engine('sqlite:///stormops_attribution.db')
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                play_id as play,
                channel,
                credit,
                touches,
                conversions
            FROM play_channel_attribution
            WHERE event_id = :event_id
            ORDER BY touches DESC
        """), {'event_id': event_id})
        
        rows = result.fetchall()
        
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows, columns=['Play', 'Channel', 'Credit', 'Touches', 'Conversions'])
    df['Credit %'] = (df['Credit'] * 100).round(1)
    
    return df


def get_attribution_for_event(event_id: str = 'DFW_STORM_24') -> pd.DataFrame:
    """Query attribution data for display in UI."""
    engine = create_engine('sqlite:///stormops_attribution.db')
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                channel,
                credit,
                total_journeys,
                conversions,
                timestamp
            FROM channel_attribution
            WHERE event_id = :event_id
            ORDER BY credit DESC
        """), {'event_id': event_id})
        
        rows = result.fetchall()
        
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows, columns=['Channel', 'Credit', 'Journeys', 'Conversions', 'Updated'])
    df['Credit %'] = (df['Credit'] * 100).round(1)
    
    return df


def render_attribution_panel(event_id: str = 'DFW_STORM_24'):
    """Render complete attribution panel in Streamlit UI."""
    import streamlit as st
    
    st.subheader("📊 Attribution Dashboard (Markov + Shapley)")
    
    # Channel Attribution
    st.markdown("### Channel Attribution")
    df = get_attribution_for_event(event_id)
    
    if df.empty:
        st.warning("No attribution data available. Run attribution_integration.py first.")
        return
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Journeys", df['Journeys'].iloc[0])
    with col2:
        st.metric("Conversions", df['Conversions'].iloc[0])
    with col3:
        conversion_rate = (df['Conversions'].iloc[0] / df['Journeys'].iloc[0] * 100)
        st.metric("Conversion Rate", f"{conversion_rate:.1f}%")
    
    # Display attribution table
    st.dataframe(
        df[['Channel', 'Credit %', 'Journeys', 'Conversions']],
        use_container_width=True,
        hide_index=True
    )
    
    # Bar chart
    st.bar_chart(df.set_index('Channel')['Credit %'])
    
    # Play-Level Attribution
    st.markdown("### Play-Level Attribution")
    play_df = get_play_attribution(event_id)
    
    if not play_df.empty:
        # Top plays
        play_summary = play_df.groupby('Play').agg({
            'Touches': 'sum',
            'Conversions': 'sum'
        }).sort_values('Touches', ascending=False).head(5)
        
        st.dataframe(play_summary, use_container_width=True)
        
        # Channel breakdown for top play
        top_play = play_summary.index[0]
        st.markdown(f"**Channel Mix for {top_play}:**")
        top_play_channels = play_df[play_df['Play'] == top_play].sort_values('Credit %', ascending=False)
        st.dataframe(
            top_play_channels[['Channel', 'Credit %', 'Touches', 'Conversions']],
            use_container_width=True,
            hide_index=True
        )
    
    # Control Group Results
    st.markdown("### Treatment vs Control")
    control_results = get_control_results(event_id)
    
    if control_results:
        for exp in control_results:
            with st.expander(f"📊 {exp['name']}", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Treatment", f"{exp['treatment_rate']*100:.1f}%", 
                             f"{exp['treatment_n']} properties")
                with col2:
                    st.metric("Control", f"{exp['control_rate']*100:.1f}%",
                             f"{exp['control_n']} properties")
                with col3:
                    delta_color = "normal" if exp['uplift'] >= 0 else "inverse"
                    st.metric("Uplift", f"{exp['uplift']*100:+.1f} pts",
                             f"{exp['uplift_pct']:+.1f}%", delta_color=delta_color)
    
    st.caption(f"Last updated: {df['Updated'].iloc[0]}")


if __name__ == '__main__':
    # Test display
    print("Attribution Data for DFW_STORM_24:")
    print("=" * 60)
    
    df = get_attribution_for_event('DFW_STORM_24')
    
    if not df.empty:
        print(df[['Channel', 'Credit %', 'Journeys', 'Conversions']].to_string(index=False))
        print("\n" + "=" * 60)
        print("✅ Attribution data ready for UI display")
        print("\nTo add to Streamlit UI:")
        print("  from attribution_ui import render_attribution_panel")
        print("  render_attribution_panel('DFW_STORM_24')")
    else:
        print("No data found. Run attribution_integration.py first.")
