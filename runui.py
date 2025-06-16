import streamlit as st
import pandas as pd
import sqlite3
from main import FindBusiness
import asyncio
import os
from dotenv import load_dotenv
import folium
from streamlit_folium import folium_static
from folium.plugins import Draw

# Page configuration
st.set_page_config(
    page_title="Plan Ville - Business Scanner",
    page_icon="🏢",
    layout="wide"
)

# Load environment variables
load_dotenv()

def get_db_data():
    """Retrieves data from SQLite database"""
    conn = sqlite3.connect('businesses.db')
    df = pd.read_sql_query("""
        SELECT 
            name,
            address,
            type,
            rating,
            user_ratings_total,
            website,
            phone,
            last_updated
        FROM businesses
    """, conn)
    conn.close()
    return df

def create_map(lat, lng, radius_km):
    """Creates a map with a circle showing the search area"""
    m = folium.Map(location=[lat, lng], zoom_start=12)
    
    # Add circle to show search area
    folium.Circle(
        location=[lat, lng],
        radius=radius_km * 1000,  # Convert km to meters
        color='red',
        fill=True,
        fill_color='red',
        fill_opacity=0.2,
        popup=f'Search radius: {radius_km} km'
    ).add_to(m)
    
    # Add marker for center point
    folium.Marker(
        location=[lat, lng],
        popup=f'Center: {lat:.4f}, {lng:.4f}'
    ).add_to(m)
    
    # Add drawing tools
    draw = Draw(
        draw_options={
            'circle': True,
            'circlemarker': False,
            'marker': True,
            'polygon': False,
            'polyline': False,
            'rectangle': False
        },
        edit_options={'edit': True}
    )
    draw.add_to(m)
    
    return m

def main():
    st.title("🏢 Plan Ville - Business Scanner")
    
    # Initialize session state for location data
    if 'lat' not in st.session_state:
        st.session_state.lat = 52.2297
    if 'lng' not in st.session_state:
        st.session_state.lng = 21.0122
    if 'radius' not in st.session_state:
        st.session_state.radius = 0.5
    
    # Sidebar controls
    st.sidebar.header("Scan Settings")
    
    # Location selection
    st.sidebar.subheader("Location Selection")
    
    # Manual input
    lat = st.sidebar.number_input("Latitude", value=st.session_state.lat, format="%.4f")
    lng = st.sidebar.number_input("Longitude", value=st.session_state.lng, format="%.4f")
    radius = st.sidebar.slider("Scan Radius (km)", 0.1, 5.0, value=st.session_state.radius, step=0.1)
    
    # Update session state
    st.session_state.lat = lat
    st.session_state.lng = lng
    st.session_state.radius = radius
    
    # Create and display map
    st.sidebar.info("Click on the map to select location or use drawing tools")
    m = create_map(st.session_state.lat, st.session_state.lng, st.session_state.radius)
    folium_static(m, width=800, height=600)
    
    # Display current selection
    st.sidebar.info(f"""
    Current Selection:
    - Latitude: {st.session_state.lat:.4f}
    - Longitude: {st.session_state.lng:.4f}
    - Radius: {st.session_state.radius:.1f} km
    """)
    
    # Cost estimation button
    if st.sidebar.button("Estimate Costs"):
        finder = FindBusiness()
        grid_info = finder.calculate_grid_info(
            st.session_state.lat,
            st.session_state.lng,
            st.session_state.radius
        )
        
        st.sidebar.info(f"""
        📊 Estimation:
        - Grid Points: {grid_info['total_grid_points']}
        - Estimated API Calls: {grid_info['estimated_api_calls']}
        - Estimated Cost: ${grid_info['estimated_cost_usd']}
        """)
    
    # Start scanning button
    if st.sidebar.button("Start Scanning"):
        finder = FindBusiness()
        with st.spinner("Scanning in progress..."):
            try:
                asyncio.run(finder.map_city(
                    st.session_state.lat,
                    st.session_state.lng,
                    st.session_state.radius
                ))
                st.success("Scan completed successfully!")
            except Exception as e:
                st.error(f"Error during scanning: {str(e)}")

    # Main content
    st.header("Database Data")
    
    # Get and display data
    df = get_db_data()
    
    if len(df) > 0:
        # Display data
        st.dataframe(
            df,
            column_config={
                "name": "Name",
                "address": "Address",
                "type": st.column_config.TextColumn(
                    "Type",
                    default="Unknown"
                ),
                "rating": st.column_config.NumberColumn(
                    "Rating",
                    format="%.1f ⭐"
                ),
                "user_ratings_total": "Total Ratings",
                "website": st.column_config.LinkColumn("Website"),
                "phone": "Phone",
                "last_updated": "Last Updated"
            },
            hide_index=True
        )
    else:
        st.info("Database is empty. Start scanning to collect data.")

if __name__ == "__main__":
    main() 