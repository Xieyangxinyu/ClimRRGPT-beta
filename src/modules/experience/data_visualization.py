import folium
import streamlit as st
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
from streamlit_folium import st_folium
from src.data_vis import dispatch_analyze_fn
from src.utils import load_config
from src.llms import OpenSourceModels
import re
import json
from geopy.geocoders import Nominatim
from st_pages import add_page_title
add_page_title(layout="wide", initial_sidebar_state="collapsed")

config = load_config("./src/modules/experience/data_visualization.yml")
get_response = OpenSourceModels(model=config['model']).get_response
st.session_state.config = config

@st.cache_data
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
    # Initialize Nominatim API
    geolocator = Nominatim(user_agent="Xinyu")
    
    # Get location
    location = geolocator.geocode(location_description)
    # Extract latitude and longitude
    if location:
        return (location.latitude, location.longitude)
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

def initialize_session_state():
    if "all_drawings" not in st.session_state:
        st.session_state.all_drawings = []
    if "lat_long" not in st.session_state:
        st.session_state.lat_long = None
    if "location_confirmed" not in st.session_state:
        st.session_state.location_confirmed = False
    if "data_visualizer_dispatcher" not in st.session_state:
        st.session_state.analyze_fn_dict = {}
    if "analysis" not in st.session_state:
        st.session_state.analysis = {}

initialize_session_state()

if ("goals_saved" not in st.session_state) or not st.session_state.goals_saved:
    #st.write(st.session_state.config[""])
    if st.button("Set Goals"):
        st.switch_page("experience/goal_setting.py")
elif not st.session_state.location_confirmed:
    st.write(st.session_state.config["welcome_message"])
    with st.expander("Instructions"):
        st.write(st.session_state.config["instruction_message"])
    
    location_input = st.text_input("Describe the general location:" , value=st.session_state.responses['Location'])

    if location_input:
        st.write("The location you entered is: ", location_input)
        lat_long = get_lat_long(location_input)
        if lat_long is None:
            st.warning("Please enter a valid location.")
        st.write("The resulting latitude and longitude are: ", lat_long)

        st.session_state.lat_long = lat_long
        # add color green to the word "green" in the markdown
        st.write("Choose a set of locations of interest by drawing on the map. The <span style='color:green'>green</span> cells represent the grid cells that intersect with the drawn shape.", unsafe_allow_html=True)

    if st.session_state.lat_long:
        m = folium.Map(location=st.session_state.lat_long, zoom_start=10)
        Draw(draw_options = {   
            "polyline": False,
            "marker": False,
        }).add_to(m)
    else:
        st.warning("Please enter a location first.")

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
    
    if st.session_state.lat_long:
        col1, col2 = st.columns(2)
        with col1:
            output = st_folium(m, feature_group_to_add=fg,
                                width=450, height=450)
        with col2:
            if st.button("Click Me Twice to Save Drawing and Update Grid Map"):
                if output['all_drawings'] != st.session_state.all_drawings:
                    st.session_state.all_drawings = output['all_drawings']
                    st.session_state.center = [output['center']['lat'], output['center']['lng']]
                    st.session_state.zoom = output['zoom']
            if st.button("Confirm Location"):
                if st.session_state.crossmodel is None:
                    st.warning("Please draw a shape on the map to confirm the location.")
                else:
                    st.session_state.location_confirmed = True
                    st.rerun()
else:
    st.session_state.analyze_fn_dict = dispatch_analyze_fn(st.session_state.selected_datasets)
    user_goals = st.session_state.custom_goals
    goals_text = "\n".join(f"{i+1}. {goal}" for i, goal in enumerate(user_goals))
    for dataset in st.session_state.selected_datasets:
        col3, messages = st.session_state.analyze_fn_dict[dataset](st.session_state.crossmodel)
        
        messages.append({"role": "user", "content": f"Here is my profile:\n\nProfession: {st.session_state.responses['Profession']}\n\nConcern: {st.session_state.responses['Concern']}\n\nTimeline: {st.session_state.responses['Timeline']}\n\nScope: {st.session_state.responses['Scope']}"})
        messages.append({"role": "user", "content": f"I'd like to address these goals:\n{goals_text}\n\nPlease provide the analysis based on the prompt above."})
        
        # Attach previous analyses
        for prev_dataset, prev_analysis in st.session_state.analysis.items():
            if prev_dataset != dataset:
                messages.append({"role": "system", "content": f"Previous analysis for {prev_dataset}:\n{prev_analysis}"})
        
        with col3:
            if st.button("Generate AI Analysis", key=f'analysis_{dataset}'):
                st.session_state.analysis[dataset] = get_response(messages=messages, stream = True,
                    options={"top_p": 0.95, "max_tokens": 512, "temperature": 0.7}
                )
                st.rerun()
            if dataset in st.session_state.analysis.keys():
                st.write(st.session_state.analysis[dataset])

    if len(st.session_state.analysis) == len(st.session_state.selected_datasets):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.generate_summary = st.button("Generate Summary", use_container_width=True)
        if st.generate_summary:
            combined_analysis = "\n\n".join(st.session_state.analysis.values())
            summary_prompt = f"Summarize the following analyses, focusing on the key insights related to the user's goals:\n\n{combined_analysis}"
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant summarizing climate data analyses."},
                {"role": "user", "content": f"I'd like a summary of the analyses, focusing on the key insights related to my goals:\n\n{goals_text}"},
                {"role": "user", "content": summary_prompt}
            ]
            
            with st.chat_message("assistant"):
                st.session_state.data_analysis_summary = get_response(messages=messages, stream=True,
                    options={"top_p": 0.95, "max_tokens": 1024, "temperature": 0.7}
                )
                st.rerun()
        if "data_analysis_summary" in st.session_state:
            with st.chat_message("assistant"):
                st.write(st.session_state.data_analysis_summary)
        with col2:
            if st.button("Change Location", use_container_width=True):
                st.session_state.location_confirmed = False
                st.session_state.analysis = {}
                st.rerun()
        with col3:
            if st.button("Move on to Literature Review", use_container_width=True):
                st.switch_page("experience/literature_review.py")