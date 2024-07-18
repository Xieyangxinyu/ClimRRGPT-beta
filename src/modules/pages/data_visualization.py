import folium
import streamlit as st
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
from streamlit_folium import st_folium
from src.data_vis import analyze_wildfire_perimeters, analyze_census_data
from src.data_vis.climrr import ClimRRSeasonalProjectionsFWI
from src.utils import load_config
from src.llms import OpenSourceModels
import re
import json

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
config = load_config("./src/modules/pages/data_visualization.yml")
get_response = OpenSourceModels(model=config['model']).get_response


st.title("FWI Map Display")
from geopy.geocoders import Nominatim

def parse_location(response):
    try:
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_string = json_match.group(1)
            parsed_data = json.loads(json_string)
        else:
            return []
    except json.JSONDecodeError:
        print("Invalid JSON format.")
        return []
    
    if type(parsed_data) is list:
        parsed_data = parsed_data[0]
    if type(parsed_data) is not dict:
        return []

    valid_entries = {}
    for key, item in parsed_data.items():
        if key in ["latitude", "longitude"]:
            valid_entries[key] = item
    if len(valid_entries) < 2:
        return []
    
    return valid_entries

@st.cache_data
def get_lat_long(location_description):
    if False:
        # Initialize Nominatim API
        geolocator = Nominatim(user_agent="Xinyu")
        
        # Get location
        location = geolocator.geocode(location_description)
        # Extract latitude and longitude
        if location:
            return (location.latitude, location.longitude)
        else:
            return None
    else:
        messages = [{"role": "system", "content": "You are a helpful assistant."},
                    {'role': 'user', 'content': f"Output the latitude and longitude of {location_description}. Output a JSON with keys 'latitude' and 'longitude'. Use numbers only. Do not use 'E', 'W'. Use this template: ```json```"}]
        response = get_response(messages=messages, 
                            options={"top_p": 0.6, "max_tokens": 10, "temperature": 0.2}
                    )
        location = parse_location(response)
        if location:
            return (location['latitude'], location['longitude'])
        else:
            return None
    
    
@st.cache_data
def initialize_grid_data():
    grid_cells_gdf = gpd.read_file('./data/GridCellsShapefile/GridCells.shp')
    st.session_state.crossmodel = None
    return grid_cells_gdf

if ("goals_saved" not in st.session_state) or not st.session_state.goals_saved:
    #st.write(st.session_state.config[""])
    if st.button("Set Goals"):
        st.switch_page("pages/goal_setting.py")

else:
    if "all_drawings" not in st.session_state:
        st.session_state.all_drawings = []
        st.session_state.init_text = True
        st.session_state.lat_long = None
    for dataset in st.session_state.selected_datasets:
        if dataset == 'Fire Weather Index (FWI) projections':
            st.session_state.analyze_fwi = ClimRRSeasonalProjectionsFWI(dataset).analyze

    location_input = st.text_input("Describe the general location:" , value=st.session_state.responses['Location'])

    if location_input:
        st.write("The location you entered is: ", location_input)
        lat_long = get_lat_long(location_input)
        st.session_state.lat_long = lat_long

        st.write("The resulting latitude and longitude are: ", lat_long)

        # add color green to the word "green" in the markdown
        st.write("Choose a set of locations of interest by drawing on the map. The <span style='color:green'>green</span> cells represent the grid cells that intersect with the drawn shape.", unsafe_allow_html=True)

    if st.session_state.lat_long:
        m = folium.Map(location=st.session_state.lat_long, zoom_start=10)
    else:
        m = folium.Map(location=[45.5236, -122.6750], zoom_start=10)

    Draw(draw_options = {   
                            "polyline": False,
                            "marker": False,
                        }).add_to(m)

    fg = folium.FeatureGroup(name="Grid bounds")
    grid_cells_gdf = initialize_grid_data()

    if st.session_state.all_drawings:
        combined_intersecting_cells = gpd.GeoDataFrame(columns=grid_cells_gdf.columns, crs=grid_cells_gdf.crs)
        for drawing in st.session_state.all_drawings:
            if drawing['properties'].keys() == {'radius'}:
                radius = drawing['properties']['radius']
                lon, lat = drawing['geometry']['coordinates']
                gdf_polygon = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")
                # Complete the code below
                gdf_polygon = gdf_polygon.to_crs("EPSG:3857")  # commonly used projection
                gdf_polygon['geometry'] = gdf_polygon.buffer(radius)
                
            else:
                gdf_polygon = gpd.GeoDataFrame.from_features([drawing], crs="EPSG:4326")
            gdf_polygon = gdf_polygon.to_crs(grid_cells_gdf.crs)
            intersecting_cells = gpd.sjoin(grid_cells_gdf, gdf_polygon, how="inner", predicate='intersects')
            combined_intersecting_cells = pd.concat([combined_intersecting_cells, intersecting_cells], ignore_index=True)
        
        combined_intersecting_cells = combined_intersecting_cells.drop_duplicates()

        st.session_state.crossmodel = combined_intersecting_cells
        st.session_state.crossmodel = st.session_state.crossmodel.drop(columns=['index_right'])

        # Add combined GeoDataFrame to folium map
        fg.add_child(
            folium.features.GeoJson(combined_intersecting_cells, style_function=lambda x: {'fillColor': 'green', 'color': 'green'})
        )
    else:
        st.session_state.crossmodel = None

    if location_input:
        col1, col2 = st.columns(2)
        with col1:
            output = st_folium(m, feature_group_to_add=fg, width=450, height=450)
        with col2:
            if st.button("Double Click Me to Save Drawing and Update Grid Map"):
                st.session_state.all_drawings = output['all_drawings']
                st.session_state.center = [output['center']['lat'], output['center']['lng']]
                st.session_state.zoom = output['zoom']

    if st.session_state.crossmodel is not None:
        for dataset in st.session_state.selected_datasets:
            if dataset == 'Fire Weather Index (FWI) projections':
                user_goals = st.session_state.custom_goals
                table, col3 = st.session_state.analyze_fwi()

                prompt = f"""
                    Analyze the following Fire Weather Index (FWI) data and provide a comprehensive interpretation:

                    Mean FWI Values (with Standard Deviation):

                    {table.to_string()}

                    Based on this data and the user's goals:
                    1. Describe the overall trend in FWI values from historical to end-century periods.
                    2. Identify which season(s) show the highest fire risk and how this changes over time.
                    3. Highlight any significant changes or patterns across seasons or time periods.
                    4. Contextualize the data: explaining how the FWI data and trends relate to or impact each goal.

                    Provide your analysis in a concise yet comprehensive manner, ensuring that the information is accessible to a general audience while still offering valuable insights for decision-makers. Tailor your response to address the user's specific goals. Your analysis should be within 150-200 words.

                    """
                
                goals_text = "\n".join(f"{i+1}. {goal}" for i, goal in enumerate(user_goals))

                messages = [{'role': 'system', 'content': "You are a helpful assistant that interprets climate data and relates it to specific user goals."},
                            {'role': 'user', 'content': prompt},
                            {"role": "user", "content": f"I'd like to address these goals:\n{goals_text}\n\nPlease provide the analysis based on the prompt above."}]            

                with col3:
                    if st.button("Generate Analysis"):
                        st.session_state.fwi_analysis = get_response(messages=messages, stream = True,
                            options={"top_p": 0.95, "max_tokens": 512, "temperature": 0.7}
                        )
                        st.rerun()
                    if "fwi_analysis" in st.session_state:
                        st.write(st.session_state.fwi_analysis)

            elif dataset == 'Recent fire incident data':
                analyze_wildfire_perimeters()
            elif dataset == 'Census data':
                analyze_census_data(st.session_state.crossmodel, output)