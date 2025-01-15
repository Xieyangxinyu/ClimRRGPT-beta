import folium
import streamlit as st
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
from streamlit_folium import st_folium
from src.data_vis import dispatch_analyze_fn
from src.utils import load_config
from src.llms import OpenSourceModels, OpenSourceVisionModels, OpenSourceCodingModels
import re
import json
import io
import contextlib
from geopy.geocoders import Nominatim
from st_pages import add_page_title
add_page_title(layout="wide", initial_sidebar_state="collapsed")

config = load_config("./src/modules/experience/data_visualization.yml")
get_response = OpenSourceModels(model=config['model']).get_response
get_vision_response = OpenSourceVisionModels(model=config['vision_model']).get_response
get_coding_response = OpenSourceCodingModels(model=config['coding_model']).get_response
st.session_state.config = config


# st.session_state.goals_saved = True
# st.session_state.selected_datasets = ['Recent Fire Perimeters data']
# st.session_state.questions = ["How have historical wildfire events and subsequent property value changes in similar metropolitan areas influenced policy decisions regarding infrastructure mitigation strategies?",
#                               "How do changes in wildfire risk perception and public policy influence property values in areas susceptible to wildfires?"]
# st.session_state.custom_goals = ["Analyze the historical trends of FWI in Denver, CO and identify areas with significant increases or decreases in fire risk.",
#     "Investigate scientific literature to understand how changes in wildfire risk perception and public policy have affected property values in areas similar to Denver.",
#     "Explore the relationship between changes in wildfire risk (as reflected by FWI projections) and current property value assessments and insurance premiums in different areas of Denver."]
# st.session_state.responses= {
#     "Location": "Denver, CO",
#     "Profession": "Risk Manager",
#     "Concern": "Property values",
#     "Timeline": "30 - 50 years",
#     "Scope": "changes might affect property values in different areas based on their proximity to fire risk zones and existing infrastructure mitigation strategies."
# }


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
    if "center" not in st.session_state:
        st.session_state.center = [0, 0]
    if "zoom" not in st.session_state:
        st.session_state.zoom = 10

# Function to execute code and save results
def execute_code(code):
    output_buffer = io.StringIO()
    exec_locals = {}
    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, {}, exec_locals)
    except Exception as e:
        st.error(f"Error executing code: {e}")
        print(f"Error executing code: {e}")
        return None
    return output_buffer.getvalue()

initialize_session_state()

def same_location(lat_long, center):
    return abs(lat_long[0] - center[0]) < 0.001 and abs(lat_long[1] - center[1]) < 0.001

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
                if not same_location([output['center']['lat'], output['center']['lng']], st.session_state.center):
                    st.session_state.center = [output['center']['lat'], output['center']['lng']]
                if output['zoom'] != st.session_state.zoom:
                    st.session_state.zoom = output['zoom']
            if st.button("Confirm Location"):
                if st.session_state.crossmodel is None:
                    st.warning("Please draw a shape on the map to confirm the location.")
                elif output['zoom'] != st.session_state.zoom:
                    st.warning("It seems like you've changed the zoom level. Please save the drawing again.")
                elif not same_location([output['center']['lat'], output['center']['lng']], st.session_state.center):
                    st.warning("It seems like you've changed the center of the map. Please save the drawing again.")
                else:
                    st.session_state.location_confirmed = True
                    st.rerun()
else:
    st.session_state.analyze_fn_dict = dispatch_analyze_fn(st.session_state.selected_datasets)
    user_goals = st.session_state.custom_goals
    goals_text = "\n".join(f"{i+1}. {goal}" for i, goal in enumerate(user_goals))
    for dataset in st.session_state.selected_datasets:
        results = st.session_state.analyze_fn_dict[dataset](st.session_state.crossmodel)
        try:
            col3, messages, code_messages, plots = results
        except ValueError:
            try:
                col3, messages, plots = results
                code_messages = None
            except ValueError:
                col3, messages = results
                code_messages = None
        
        messages.append({"role": "user", "content": f"Here is my profile:\n\nProfession: {st.session_state.responses['Profession']}\n\nConcern: {st.session_state.responses['Concern']}\n\nTimeline: {st.session_state.responses['Timeline']}\n\nScope: {st.session_state.responses['Scope']}"})
        messages.append({"role": "user", "content": f"Please provide the analysis of the data based on the prompt above, ensuring the discussion aligns with and reflects the goals outlined here: \n\n{goals_text}"})

        # Attach previous analyses
        for prev_dataset, prev_analysis in st.session_state.analysis.items():
            if prev_dataset != dataset:
                messages = [messages[0]] + [{"role": "system", "content": f"Previous analysis for {prev_dataset}:\n{prev_analysis}"}] + messages[1:]

        col1, col2 = st.columns(2)
        with col3:
            # Define a toggle in session state if it doesn't exist
            if f'response_view_{dataset}' not in st.session_state:
                st.session_state[f'response_view_{dataset}'] = 'init'  # start by showing the new response

            get_ai_analysis = st.button("Generate AI Analysis", key=f'get_ai_analysis_{dataset}')
            if get_ai_analysis:
                #st.markdown('**Querying the LLM at the backend...**')
                print('Querying LLM')
                print('messages', messages)
                llm_response = get_response(messages=messages, stream=True,
                    options={"top_p": 0.95, "max_tokens": 512, "temperature": 0.2}
                )
                # st.session_state.analysis[dataset] = llm_response
                st.session_state[f'old_response_{dataset}'] = llm_response  # Save the old response immediately
                print('llm_response', llm_response)

                if code_messages is not None:
                    st.markdown(
                        "<p style='font-size:small; font-style:italic;'>Feel free to read now! We will double-check it in the backend with data analysis model for better accuracy...</p>",
                        unsafe_allow_html=True
                    )

                    print('Querying CodingLLM')
                    code_from_llm = get_coding_response(messages=code_messages, stream=False,
                                                        options={"top_p": 0.95, "max_tokens": 512, "temperature": 0.2}
                                                    )
                    code_from_llm = code_from_llm[9:-3]
                    print('code_from_llm', code_from_llm)
                    execution_results = execute_code(code_from_llm)
                    print('execution results', execution_results)

                    # print('Querying VLM')
                    # vlm_messages = [{"role": "user",
                    #                  "content": vision_messages,
                    #                  'images': plots}]
                    # vlm_response = get_vision_response(messages=vlm_messages, stream=False,
                    #                                    options={"top_p": 0.95, "max_tokens": 512, "temperature": 0.2}
                    #                                    )
                    # print('vlm_response', vlm_response)
                    # st.markdown(
                    #     "<p style='font-size:small; font-style:italic;'>If needed, an updated analysis will be shown here automatically......</p>",
                    #     unsafe_allow_html=True
                    # )

                    if execution_results is not None:
                        print('Querying LLM')
                        messages.append({"role": "user",
                                        "content": "Update your original analysis given this additional information:" + execution_results +
                                                    "\n\nCheck if there is any contradictory information and if any, fix the original ones. "
                                                    "Please keep your original analysis unchanged except for the parts that need to be updated or corrected."
                                                    "You must mention everything mentioned in this additional information. "
                                                    "Use bold fonts to highlight the updated parts. Here is the original analysis:\n" + llm_response})
                        final_response = get_response(messages=messages, stream=False,
                                                    options={"top_p": 0.95, "max_tokens": 512, "temperature": 0.2}
                                                    )
                        print('final_response', final_response)
                        # st.session_state.analysis[dataset] = final_response
                        st.session_state[f'new_response_{dataset}'] = final_response  # Save the final response

                    st.session_state[f'response_view_{dataset}'] = 'final'  # Set to show final response after processing
                    st.rerun()

                # Handle the toggling and display of responses
                if f'old_response_{dataset}' in st.session_state and f'new_response_{dataset}' in st.session_state:
                    # Toggle between responses
                    if st.session_state[f'response_view_{dataset}'] == 'final':
                        show_init_response = st.button("Switch response", key=f'toggle_old_{dataset}')
                        if show_init_response:
                            st.session_state[f'response_view_{dataset}'] = 'prev'
                    elif st.session_state[f'response_view_{dataset}'] == 'prev':
                        show_final_response = st.button("Switch response", key=f'toggle_old_{dataset}')
                        if show_final_response:
                            st.session_state[f'response_view_{dataset}'] = 'final'

                    # Display the appropriate response
                    if st.session_state[f'response_view_{dataset}'] == 'final':
                        st.markdown(st.session_state[f'new_response_{dataset}'])
                    elif st.session_state[f'response_view_{dataset}'] == 'prev':
                        st.markdown('**Original Analysis**')
                        st.markdown(st.session_state[f'old_response_{dataset}'])

            if dataset in st.session_state.analysis.keys():
                input_data = st.session_state.analysis[dataset]
                with col2:
                    allow_editing = st.radio("Edit Analysis", ['Edit', 'Save'], horizontal=True, key = f'edit_{dataset}', index=1, label_visibility="collapsed")

                if allow_editing == 'Edit':
                    num_rows = int((len(st.session_state.analysis[dataset]) // 50 + 1)  * 21)
                    output = st.text_area("Analysis", value=st.session_state.analysis[dataset], height=num_rows, label_visibility="collapsed")
                    st.session_state.analysis[dataset] = output
                else:
                    st.write(st.session_state.analysis[dataset])

    col1, col2, col3 = st.columns(3)
    if len(st.session_state.analysis) == len(st.session_state.selected_datasets):
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
                    options={"top_p": 0.95, "max_tokens": 1024, "temperature": 0.2}
                )
                st.rerun()
        if "data_analysis_summary" in st.session_state:
            with st.chat_message("assistant"):
                st.write(st.session_state.data_analysis_summary)
    with col2:
        if st.button("Change Location", use_container_width=True):
            st.session_state.location_confirmed = False
            st.session_state.crossmodel = None
            st.session_state.all_drawings = []
            st.session_state.analysis = {}
            st.rerun()
    with col3:
        if st.button("Move on to Literature Review", use_container_width=True):
            st.switch_page("experience/literature_review.py")