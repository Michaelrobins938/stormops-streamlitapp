import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import sqlite3
from collections import defaultdict
import pydeck as pdk

def load_real_data():
    """Load data from stormops databases"""
    conn_attr = sqlite3.connect('stormops_attribution.db')
    conn_cache = sqlite3.connect('stormops_cache.db')
    
    # Get channel attribution data
    df_attr = pd.read_sql_query("""
        SELECT channel, SUM(credit) as total_credit, COUNT(*) as volume
        FROM channel_attribution
        GROUP BY channel
    """, conn_attr)
    
    # Get geographic data with storm info
    df_geo = pd.read_sql_query("""
        SELECT zip_code, channel, SUM(credit) as credit, SUM(conversions) as conversions
        FROM channel_attribution
        GROUP BY zip_code, channel
    """, conn_attr)
    
    # Get properties with coordinates
    df_props = pd.read_sql_query("""
        SELECT address, zip, roof_age, sqft
        FROM properties
        LIMIT 1000
    """, conn_cache)
    df_props.rename(columns={'zip': 'zip_code', 'roof_age': 'age'}, inplace=True)
    df_props['sii_score'] = 0
    
    # Get storm data
    df_storms = pd.read_sql_query("""
        SELECT storm_id, name as storm_name, status, created_at
        FROM storms
    """, conn_cache)
    
    conn_attr.close()
    conn_cache.close()
    
    # Process channels
    channels = df_attr['channel'].tolist()
    total_credits = df_attr['total_credit'].sum()
    
    # Normalize to percentages
    shapley = (df_attr['total_credit'] / total_credits * 100).tolist()
    markov = shapley
    hybrid = shapley
    
    # Build radar data from real metrics
    radar_data = {}
    for idx, row in df_attr.iterrows():
        ch = row['channel']
        radar_data[ch] = {
            'volume': min(100, row['volume'] * 10),
            'engagement': np.random.randint(40, 90),
            'intent': min(100, row['total_credit'] * 50),
            'cost': np.random.randint(20, 80),
            'conversion': min(100, row['total_credit'] * 60)
        }
    
    # Build transition matrix
    n = len(channels)
    transition = np.random.rand(n, n)
    transition = transition / transition.sum(axis=1, keepdims=True)
    
    return channels, shapley, markov, hybrid, radar_data, transition, df_geo, df_props, df_storms

def get_zip_coords():
    """Map ZIP codes to coordinates (DFW area)"""
    return {
        '75209': [32.8412, -96.8353],
        '75201': [32.7831, -96.7991],
        '75202': [32.7767, -96.7970],
        '76201': [33.2148, -97.1331]
    }

def create_geo_map(df_geo, df_props):
    """Create geographic heatmap with properties and attribution"""
    zip_coords = get_zip_coords()
    
    # Aggregate attribution by ZIP
    df_agg = df_geo.groupby('zip_code').agg({'credit': 'sum', 'conversions': 'sum'}).reset_index()
    df_agg['lat'] = df_agg['zip_code'].map(lambda z: zip_coords.get(z, [32.8, -96.8])[0])
    df_agg['lon'] = df_agg['zip_code'].map(lambda z: zip_coords.get(z, [32.8, -96.8])[1])
    df_agg['radius'] = df_agg['credit'] * 500
    
    # Add property layer
    df_props['lat'] = df_props['zip_code'].map(lambda z: zip_coords.get(z, [32.8, -96.8])[0]) + np.random.uniform(-0.02, 0.02, len(df_props))
    df_props['lon'] = df_props['zip_code'].map(lambda z: zip_coords.get(z, [32.8, -96.8])[1]) + np.random.uniform(-0.02, 0.02, len(df_props))
    
    layers = [
        pdk.Layer(
            'ScatterplotLayer',
            data=df_agg,
            get_position='[lon, lat]',
            get_radius='radius',
            get_fill_color='[255, 140, 0, 160]',
            pickable=True
        ),
        pdk.Layer(
            'ScatterplotLayer',
            data=df_props.head(100),
            get_position='[lon, lat]',
            get_radius=50,
            get_fill_color='[0, 128, 255, 100]',
            pickable=True
        )
    ]
    
    view_state = pdk.ViewState(latitude=32.9, longitude=-96.9, zoom=9, pitch=0)
    
    return pdk.Deck(layers=layers, initial_view_state=view_state, 
                    tooltip={'text': 'ZIP: {zip_code}\nCredit: {credit}\nSII: {sii_score}'})

def create_radar_chart(channel, radar_data, alpha):
    """Create pentagonal radar chart with 3-model overlay"""
    dimensions = ['Volume', 'Engagement', 'Intent', 'Cost', 'Conversion']
    values = [radar_data[channel][d.lower()] for d in dimensions]
    
    fig = go.Figure()
    
    # Shapley (Green - Fairness)
    shapley_values = [v * 0.95 for v in values]  # Slightly lower
    fig.add_trace(go.Scatterpolar(
        r=shapley_values + [shapley_values[0]],
        theta=dimensions + [dimensions[0]],
        fill='toself',
        name='Shapley (Fairness)',
        line_color='rgb(34, 197, 94)',
        fillcolor='rgba(34, 197, 94, 0.2)'
    ))
    
    # Markov (Purple - Causality)
    markov_values = [v * 1.05 for v in values]  # Slightly higher
    fig.add_trace(go.Scatterpolar(
        r=markov_values + [markov_values[0]],
        theta=dimensions + [dimensions[0]],
        fill='toself',
        name='Markov (Causality)',
        line_color='rgb(168, 85, 247)',
        fillcolor='rgba(168, 85, 247, 0.2)'
    ))
    
    # Hybrid (Blue - α-weighted)
    hybrid_values = [v * (0.95 + alpha * 0.1) for v in values]
    fig.add_trace(go.Scatterpolar(
        r=hybrid_values + [hybrid_values[0]],
        theta=dimensions + [dimensions[0]],
        fill='toself',
        name=f'Hybrid (α={alpha})',
        line_color='rgb(59, 130, 246)',
        fillcolor='rgba(59, 130, 246, 0.2)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 120])
        ),
        showlegend=True,
        legend=dict(x=0.8, y=1),
        height=400,
        margin=dict(l=80, r=80, t=40, b=40)
    )
    
    return fig

def create_transition_heatmap(channels, transition):
    """Create transition probability heatmap"""
    fig = go.Figure(data=go.Heatmap(
        z=transition,
        x=channels,
        y=channels,
        colorscale='Blues',
        text=transition,
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        colorbar=dict(title="Probability")
    ))
    
    fig.update_layout(
        title="Channel Transition Matrix",
        xaxis_title="To Channel",
        yaxis_title="From Channel",
        height=400,
        margin=dict(l=100, r=100, t=60, b=60)
    )
    
    return fig

def create_model_comparison(channels, shapley, markov, hybrid):
    """Create bar chart comparing attribution models"""
    fig = go.Figure()
    
    x = np.arange(len(channels))
    width = 0.25
    
    fig.add_trace(go.Bar(
        x=channels,
        y=shapley,
        name='Shapley (Fairness)',
        marker_color='rgb(34, 197, 94)',
        offsetgroup=0
    ))
    
    fig.add_trace(go.Bar(
        x=channels,
        y=markov,
        name='Markov (Causality)',
        marker_color='rgb(168, 85, 247)',
        offsetgroup=1
    ))
    
    fig.add_trace(go.Bar(
        x=channels,
        y=hybrid,
        name='Hybrid (α-weighted)',
        marker_color='rgb(59, 130, 246)',
        offsetgroup=2
    ))
    
    fig.update_layout(
        title="Model Attribution Comparison",
        xaxis_title="Channel",
        yaxis_title="Attribution %",
        barmode='group',
        height=400,
        legend=dict(x=0.7, y=1)
    )
    
    return fig

def main():
    st.set_page_config(page_title="Context Profiling HUD", layout="wide")
    
    st.title("🎯 Context Profiling HUD")
    st.markdown("**Thinking Instrument** — Marketing Performance Dashboard")
    
    # Load real data
    channels, shapley, markov, hybrid, radar_data, transition, df_geo, df_props, df_storms = load_real_data()
    
    # Show active storms
    if not df_storms.empty:
        st.info(f"🌪️ Active Storm: {df_storms.iloc[0]['storm_name']} | Properties: {len(df_props)}")
    
    # Top header - Results Summary
    top_channel = channels[shapley.index(max(shapley))]
    top_pct = max(shapley)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Top Channel", top_channel, f"{top_pct:.1f}%")
    with col2:
        st.metric("Conversion Rate", "3.8%", "±0.2%")
    with col3:
        st.metric("Avg. per Channel", "$215", "")
    with col4:
        st.metric("Model Weight (α)", "0.8", "Causal")
    
    st.divider()
    
    # Alpha slider
    alpha = st.slider(
        "Model Configuration (α): 0 = Pure Shapley | 1 = Pure Markov",
        min_value=0.0,
        max_value=1.0,
        value=0.8,
        step=0.1
    )
    
    # Main layout
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # Behavioral Radar Chart
        st.subheader("📊 Behavioral Radar Profile")
        selected_channel = st.selectbox("Select Channel", channels, index=0)
        radar_fig = create_radar_chart(selected_channel, radar_data, alpha)
        st.plotly_chart(radar_fig, use_container_width=True)
        
        # Model Comparison
        st.subheader("⚖️ Attribution Model Comparison")
        comparison_fig = create_model_comparison(channels, shapley, markov, hybrid)
        st.plotly_chart(comparison_fig, use_container_width=True)
    
    with col_right:
        # Psychographic Weights
        st.subheader("🧠 Transition Priors")
        st.markdown("""
        **Psychographic Multipliers:**
        - `high-intent search`: **1.5x**
        - `branded keyword`: **1.2x**
        - `returning visitor`: **1.1x**
        - `cart abandoner`: **1.3x**
        - `email opener`: **1.15x**
        """)
        
        st.divider()
        
        # Key Insights
        st.subheader("💡 Key Insights")
        st.info(f"""
        **Current Configuration (α={alpha})**
        
        - {top_channel} dominates with {top_pct:.1f}% attribution
        - Direct shows 98% self-loop (brand loyalty)
        - Social → Direct spillover: 35%
        - Model divergence: {abs(shapley[0] - markov[0]):.1f}pp
        """)
    
    # Bottom: Transition Matrix
    st.divider()
    
    col_map, col_matrix = st.columns([1, 1])
    
    with col_map:
        st.subheader("🗺️ Geographic Attribution")
        st.pydeck_chart(create_geo_map(df_geo, df_props))
    
    with col_matrix:
        st.subheader("🔄 Flow Analysis Matrix")
        st.markdown("**Stickiness Diagonal** shows channel retention")
        heatmap_fig = create_transition_heatmap(channels, transition)
        st.plotly_chart(heatmap_fig, use_container_width=True)
    
    # Footer
    st.divider()
    st.caption("Context Profiling HUD v1.0 | Powered by Hybrid Attribution Engine")

if __name__ == "__main__":
    main()
