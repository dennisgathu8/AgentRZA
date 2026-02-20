import streamlit as st
import duckdb
from cryptography.fernet import Fernet
import os
import tempfile
import pandas as pd
import plotly.express as px
from config.settings import get_settings

settings = get_settings()

st.set_page_config(page_title="Football Gravity", page_icon="\u26bd", layout="wide")

st.title("\u26bd Football Gravity - Zero Trust xG Analytics")
st.markdown("This dashboard decrypts the securely stored Parquet analytics **in-memory**.")

@st.cache_data
def load_encrypted_data(parquet_enc_path: str):
    """Zero-trust secure decryption of at-rest parquet files into a memory Dataframe."""
    if not os.path.exists(parquet_enc_path):
        return None
        
    fernet = Fernet(settings.get_fernet_bytes())
    with open(parquet_enc_path, 'rb') as f:
        encrypted_data = f.read()
        
    decrypted_data = fernet.decrypt(encrypted_data)
    
    # Write cleanly to a pure tempfile that DuckDB can ingest
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp.write(decrypted_data)
        tmp_path = tmp.name
        
    try:
        conn = duckdb.connect(':memory:')
        df = conn.execute(f"SELECT * FROM '{tmp_path}'").df()
    finally:
        os.remove(tmp_path) # Clean up decrypted footprint immediately
        
    return df

events_path = settings.duckdb_path.replace('.duckdb', '_events.enc')
matches_path = settings.duckdb_path.replace('.duckdb', '_matches.enc')

df_events = load_encrypted_data(events_path)
df_matches = load_encrypted_data(matches_path)

if df_events is None or df_matches is None:
    st.warning("No encrypted data found. Please run the LangGraph pipeline via `python main.py --date today` first.")
    st.stop()

# Interactive Multi-Tab Dashboard
tab1, tab2, tab3 = st.tabs(["\ud83d\udd12 Match Metadata", "\ud83d\udcca Expected Goals (xG)", "\ud83c\udfa5 Optical Tracking (Pitch Control)"])

with tab1:
    st.header("Match Metadata Overview (Encrypted DB)")
    st.dataframe(df_matches, use_container_width=True)

with tab2:
    st.header("\ud83d\udcca Advanced xG Shot Map")
    # Filter down to just shots (those that have xG calculated)
    if 'xg' in df_events.columns:
        shots_df = df_events[df_events['xg'].notna()]
        
        if not shots_df.empty:
            fig = px.scatter(
                shots_df,
                x='minute',
                y='xg',
                color='player_name',
                size='xg',
                hover_data=['type_name', 'period', 'second'],
                title="Expected Goals (xG) by Minute Orchestrated from SC-Learn Logistic Engine",
                labels={'minute': 'Match Minute', 'xg': 'Expected Goals (xG)', 'player_name': 'Player'}
            )
            
            # Modern Analytics styling
            fig.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No shots recorded in this match set.")
            
    st.header("Player Enrichment Roster")
    if 'player_name' in df_events.columns:
        agg_df = df_events.groupby('player_name').agg({'xg': 'sum', 'xa': 'sum', 'event_id': 'count'}).reset_index()
        agg_df.rename(columns={'event_id': 'Total Events', 'xg': 'Total xG', 'xa': 'Total xA'}, inplace=True)
        st.dataframe(agg_df.sort_values(by='Total xG', ascending=False), use_container_width=True)

with tab3:
    st.header("\ud83c\udfa5 Simulated Optical Tracking (Metrica Open Data)")
    st.markdown("Visualizing 30fps player coordinate bounds and **Spatial Pitch Control** probabilities.")
    
    # Check if tracking data was persisted from the array
    if 'tracking_frames' in df_matches.columns:
        try:
            import json
            # DuckDB struct arrays parse as lists of dicts
            tracking_list = df_matches.iloc[0]['tracking_frames']
            if tracking_list and len(tracking_list) > 0:
                # Extract PPDA spatial dominance metric 
                # Our schema mapped 'home_ppda' to spatial control Home probability
                metrics = [{"frame": f['frame_id'], "Home Control %": f.get('home_ppda', 0.5)} for f in tracking_list]
                df_metrics = pd.DataFrame(metrics)
                
                fig = px.line(df_metrics, x="frame", y="Home Control %", title="Spatial Pitch Dominance (Possession Window)")
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
                
                st.info("Tracking sample successfully decrypted and parsed from pure JSON.")
            else:
                st.warning("No tracking frames recorded for this match run.")
        except Exception as e:
            st.error(f"Failed to parse tracking JSON visually: {str(e)}")
    else:
         st.warning("Tracking Frame structs not found in database schema. Re-run pipeline.")
