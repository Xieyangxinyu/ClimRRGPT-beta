import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd
from census import Census
from pygris.geocode import geolookup
from branca.colormap import linear

@st.cache_data
def get_state_bg(state_code):
    return gpd.read_file(f"https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_{state_code}_bg.zip")

def analyze_census_data(cross_model, output):
    st.title("Census Data")
    c = Census("93c3297165ad8b5b6c81e0ed9e2e44a38e56224f")
    geocode = geolookup(longitude = output['center']['lng'], latitude= output['center']['lat'])['GEOID'][0]
    state_code = geocode[0:2]

    state_tract = get_state_bg(state_code)
    state_tract = state_tract.to_crs(crs=cross_model.crs)
    state_tract["GEOID"] = state_tract["GEOID"].astype(str)
    # intersect with the cross_model
    state_tract = gpd.sjoin(state_tract, cross_model, how="inner", predicate='intersects')
    state_tract = state_tract[['GEOID', 'geometry']].drop_duplicates()

    block_groups = c.acs5.state_county_blockgroup(fields = ('C17002_001E', 'C17002_002E', 'C17002_003E', 'B01003_001E', 'B25001_001E', 'B19013_001E'),
        state_fips = state_code,
        county_fips = '*',
        tract = '*',
        blockgroup = "*",
        year = 2022)
    bg_df = pd.DataFrame(block_groups)

    bg_df["GEOID"] = bg_df["state"] + bg_df["county"] + bg_df["tract"] + bg_df["block group"]
    bg_df["GEOID"] = bg_df["GEOID"].astype(str)
    bg_df = state_tract.merge(bg_df, on = "GEOID")
    bg_df = bg_df[['GEOID', 'C17002_003E', 'C17002_002E', 'B01003_001E', 'B25001_001E', 'geometry']]


    color_scale = linear.YlOrRd_09.scale(bg_df['B01003_001E'].min(), bg_df['B01003_001E'].max())

    bg_df['poverty_count'] = bg_df['C17002_002E'] + bg_df['C17002_003E'] 
    bg_df['poverty_rate'] = bg_df['poverty_count'] / bg_df['B01003_001E']
    # if the poverty rate is NaN, set it to 0
    bg_df['poverty_rate'] = bg_df['poverty_rate'].fillna(0)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("Population")
        m6 = folium.Map(location=st.session_state.lat_long, zoom_start=st.session_state.zoom)
        m6.add_child(
            # color based on population
            folium.features.GeoJson(bg_df, tooltip = folium.features.GeoJsonTooltip(fields=['GEOID','poverty_rate', 'B01003_001E', 'B25001_001E'], aliases=['GEOID', 'Poverty Rate', 'Population', 'Housing Units']),
                                    style_function=lambda x: {
                                        'fillColor': color_scale(bg_df[bg_df['GEOID'] == x['properties']['GEOID']]['B01003_001E'].values[0]),
                                        'color': 'black',  # Boundary color
                                        'weight': 1,  # Boundary weight
                                        'fillOpacity': 0.7
                                    },)
        )
        # add legend
        m6.add_child(color_scale)
        st_folium(m6, width=450, height=450)
    with col2:
        st.write("Poverty Rate")
        m7 = folium.Map(location=st.session_state.lat_long, zoom_start=st.session_state.zoom)
        color_scale = linear.YlOrRd_09.scale(bg_df['poverty_rate'].min(), bg_df['poverty_rate'].max())
        m7.add_child(
            # color based on poverty rate
            folium.features.GeoJson(bg_df, tooltip = folium.features.GeoJsonTooltip(fields=['GEOID','poverty_rate', 'B01003_001E', 'B25001_001E'], aliases=['GEOID', 'Poverty Rate', 'Population', 'Housing Units']),
                                    style_function=lambda x: {
                                        'fillColor': color_scale(bg_df[bg_df['GEOID'] == x['properties']['GEOID']]['poverty_rate'].values[0]),
                                        'color': 'black',  # Boundary color
                                        'weight': 1,  # Boundary weight
                                        'fillOpacity': 0.7
                                    },)
        )
        # add legend
        m7.add_child(color_scale)
        st_folium(m7, width=450, height=450)
    with col3:
        st.write("Housing Units")
        m8 = folium.Map(location=st.session_state.lat_long, zoom_start=st.session_state.zoom)
        color_scale = linear.YlOrRd_09.scale(bg_df['B25001_001E'].min(), bg_df['B25001_001E'].max())
        m8.add_child(
            # color based on housing units
            folium.features.GeoJson(bg_df, tooltip = folium.features.GeoJsonTooltip(fields=['GEOID','poverty_rate', 'B01003_001E', 'B25001_001E'], aliases=['GEOID', 'Poverty Rate', 'Population', 'Housing Units']),
                                    style_function=lambda x: {
                                        'fillColor': color_scale(bg_df[bg_df['GEOID'] == x['properties']['GEOID']]['B25001_001E'].values[0]),
                                        'color': 'black',  # Boundary color
                                        'weight': 1,  # Boundary weight
                                        'fillOpacity': 0.7
                                    },)
        )
        # add legend
        m8.add_child(color_scale)
        st_folium(m8, width=450, height=450)

    col1, col2 = st.columns(2)
    with col1:
        display = bg_df[['GEOID', 'poverty_rate', 'B01003_001E', 'B25001_001E']]
        display = display.rename(columns={'poverty_rate': 'Poverty Rate', 'B01003_001E': 'Population', 'B25001_001E': 'Housing Units'})
        st.dataframe(display, hide_index=True)
    with col2:
        st.write("## Regional Summary")
        st.write("Total Population: ", bg_df['B01003_001E'].sum())
        st.write("Total Poverty Rate (Total Poverty Count / Total Population): ", bg_df["poverty_count"].sum() / bg_df["B01003_001E"].sum())
        st.write("Total Housing Units: ", bg_df['B25001_001E'].sum())