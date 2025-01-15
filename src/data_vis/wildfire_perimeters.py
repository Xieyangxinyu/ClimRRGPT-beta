import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import json
from src.utils import load_config

@st.cache_data
def get_perimeters_data():
    perimeters = gpd.read_file('./data/WFIGS_Interagency_Perimeters/Perimeters.shp')
    perimeters = perimeters[perimeters['attr_Inc_4'] == 'WF']
    return perimeters

def load_prompt(report, tabs_content):

    # TODO: This formatted prompt kept outputing errors; need to fix it

    config = load_config('src/data_vis/wildfire_perimeters.yml')
    yearly_acres = tabs_content.get('Burned Acres and Dates', pd.DataFrame())
    fire_causes = tabs_content.get('Fire Cause Analysis', pd.DataFrame())
    fire_behaviors = tabs_content.get('Fire Behavior', pd.DataFrame())
    fuels = tabs_content.get('Fuels')
    
    prompt = config['prompt']

    # Format the data for the prompt
    data = {
        'yearly_acres': yearly_acres[['Year', 'Total Acres']],
        'yearly_incidents': yearly_acres[['Year', 'Number of Incidents']],
        'avg_containment_time': report.groupby('Year')['Containment Time'].mean(),
        'top_specific_causes': fire_causes.head().to_dict(),
        'top_specific_behaviors': fire_behaviors.head().to_dict(),
        'top_primary_fuels': fuels[0].head().to_dict(),
        'top_secondary_fuels': fuels[1].head().to_dict(),
    }

    # Format the prompt with the data
    formatted_prompt = prompt.format(**{k: json.dumps(v, indent=2) for k, v in data.items()})
    messages = [
        {'role': 'system', 'content': 'You are a helpful assistant who provides insights on wildfire perimeters.'},
        {'role': 'user', 'content': formatted_prompt}
        ]
    return messages

def analyze_wildfire_perimeters(cross_model):
    st.title("Wildfire Perimeters Analysis")
    st.write("""
    This analysis is based on the Wildland Fire Incident Geospatial Information System (WFIGS) Interagency Perimeters dataset. 
    It provides comprehensive information about wildfire incidents, including their location, size, cause, behavior, and timeline.
    
    Key features of the dataset include:
    - Incident Name and Acres: Identifies each fire and its affected area.
    - Fire Cause: Categorized into broad, general, and specific causes.
    - Fire Timeline: Includes discovery, containment, and control dates.
    - Fire Behavior: Describes how the fire reacted to fuel, weather, and topography.
    - Fuel Models: Indicates the primary and secondary types of fuel carrying the fire.
    
    The data covers wildfire incidents from 2020 to 2024, allowing for analysis of recent trends and patterns in wildfire occurrences.
    """)

    perimeters = get_perimeters_data()

    rename_map = {
        'attr_Inc_2': 'Incident Name',
        'poly_GISAc': 'Incident Acres',
        'attr_FireC': 'Fire Cause (Broad)',
        'attr_Fir_4': 'Fire Cause (General)',
        'attr_Fir_5': 'Fire Cause (Specific)',
        'attr_Fir_7': 'Fire Discovery Date',
        'attr_Conta': 'Containment Date',
        'attr_Contr': 'Control Date',
        'attr_FireB': 'Fire Behavior',
        'attr_Fir_1': 'Fire Behavior (More Specific)',
        'attr_Prima': 'Primary Fuel Model',
        'attr_Secon': 'Secondary Fuel Model',
    }

    perimeters = perimeters.to_crs(cross_model.crs)
    perimeters = gpd.sjoin(perimeters, cross_model, how="inner", predicate='intersects')
    report = perimeters[list(rename_map.keys()) + ['geometry']]
    report = report.rename(columns=rename_map)

    # Data cleaning
    report = report.drop_duplicates()
    report['Fire Discovery Date'] = pd.to_datetime(report['Fire Discovery Date'])
    report['Containment Date'] = pd.to_datetime(report['Containment Date'])
    report['Control Date'] = pd.to_datetime(report['Control Date'])
    report.loc[report['Containment Date'] < report['Fire Discovery Date'], 'Containment Date'] = None
    report.loc[report['Control Date'] < report['Fire Discovery Date'], 'Control Date'] = None
    report['Year'] = report['Fire Discovery Date'].dt.year

    # Year range slider
    year_range = st.slider("Select Year Range", min_value=2020, max_value=2024, value=(2020, 2024))
    filtered_report = report[(report['Year'] >= year_range[0]) & (report['Year'] <= year_range[1])]
    display_report = filtered_report.copy()

    col1, col2 = st.columns([1, 2])
    # Map visualization
    m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
    fg = folium.FeatureGroup(name="Perimeters")
    # if Date is in the report, change the data type to string
    date_columns = ['Fire Discovery Date', 'Containment Date', 'Control Date']
    for col in date_columns:
        filtered_report[col] = filtered_report[col].astype(str)

    fg.add_child(
        folium.features.GeoJson(
            filtered_report,
            tooltip=folium.features.GeoJsonTooltip(fields=list(rename_map.values())[:-2], aliases=list(rename_map.values())[:-2]),
            style_function=lambda x: {'fillColor': 'red', 'color': 'red'}
        )
    )
    with col1:
        st_folium(m, feature_group_to_add=fg, width=450, height=450)

    with col2:
        display_report.drop(columns=['geometry'], inplace=True)
        display_report = display_report.sort_values(by='Fire Discovery Date', ascending=True)
        display_report = display_report.reset_index(drop=True)
        # drop columns with all null values
        display_report = display_report.dropna(axis=1, how='all')
        st.dataframe(display_report, hide_index=True)

    # Prepare tabs
    tabs = []
    tab_contents = []

    # Tab 1: Burned Acres and Dates
    if not report['Incident Acres'].isnull().all() and not report['Containment Date'].isnull().all():
        tabs.append("Burned Acres and Dates")
        tab_contents.append(lambda: burned_acres_and_dates_tab(report))

    # Tab 2: Fire Cause Analysis
    if not report['Fire Cause (Broad)'].isnull().all() and not report['Fire Cause (Specific)'].isnull().all():
        tabs.append("Fire Cause Analysis")
        tab_contents.append(lambda: fire_cause_analysis_tab(report))

    # Tab 3: Fire Behavior
    if not report['Fire Behavior'].isnull().all() and not report['Fire Behavior (More Specific)'].isnull().all():
        tabs.append("Fire Behavior")
        tab_contents.append(lambda: fire_behavior_tab(report))

    # Tab 4: Fuels
    if not report['Primary Fuel Model'].isnull().all() and not report['Secondary Fuel Model'].isnull().all():
        tabs.append("Fuels")
        tab_contents.append(lambda: fuels_tab(report))

    tabs_content = {}
    # Create tabs
    if tabs:
        tab_objects = st.tabs(tabs)
        for tab, tab_obj, content in zip(tabs, tab_objects, tab_contents):
            with tab_obj:
                tabs_content[tab] = content()
    else:
        st.warning("No data available for analysis.")

    col1, col2 = st.columns([5,1])
    messages = load_prompt(report, tabs_content)
    #messages = []
    return col1, messages

def burned_acres_and_dates_tab(report):
    st.header("Burned Acres and Dates")
    
    # Total acres burned per year
    yearly_acres = report.groupby('Year')['Incident Acres'].agg(['sum', 'count']).reset_index()
    yearly_acres = yearly_acres.rename(columns={'sum': 'Total Acres', 'count': 'Number of Incidents'})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        fig1 = px.line(yearly_acres, x='Year', y='Total Acres', title='Total Acres Burned per Year')
        st.plotly_chart(fig1)

    with col2:
        fig2 = px.line(yearly_acres, x='Year', y='Number of Incidents', title='Number of Incidents per Year')
        st.plotly_chart(fig2)

    with col3:
    # Average containment time
        report['Containment Time'] = (report['Containment Date'] - report['Fire Discovery Date']).dt.total_seconds() / (24 * 60 * 60)
        avg_containment_time = report.groupby('Year')['Containment Time'].mean().reset_index()
        fig3 = px.line(avg_containment_time, x='Year', y='Containment Time', title='Average Containment Time (Days) per Year')
        st.plotly_chart(fig3)
    with col4:
        st.write("Yearly Summary:")
        for _, row in yearly_acres.iterrows():
            st.write(f"Year {row['Year']}: {row['Total Acres']:.2f} acres burned in {row['Number of Incidents']} incidents")

    return yearly_acres

def fire_cause_analysis_tab(report):
    st.header("Fire Cause Analysis")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # Broad fire causes
        broad_causes = report['Fire Cause (Broad)'].value_counts().reset_index()
        fig3 = px.pie(broad_causes, values='count', names='Fire Cause (Broad)', title='Distribution of Broad Fire Causes')
        st.plotly_chart(fig3)
    with col2:
        # All specific fire causes
        specific_causes = report['Fire Cause (Specific)'].value_counts().reset_index()
        fig4 = px.bar(specific_causes, x='Fire Cause (Specific)', y='count', title='Specific Fire Causes')
        st.plotly_chart(fig4)

    with col3:
        # List top 5 (or fewer) specific fire causes
        top_items = specific_causes.head(5)
        st.write(f"Top {len(top_items)} Specific Fire Cause{'s' if len(top_items) > 1 else ''}:")
        for i, (cause, count) in enumerate(zip(top_items['Fire Cause (Specific)'], top_items['count']), 1):
            st.write(f"{i}. {cause}: {count}")
    return top_items

def fire_behavior_tab(report):
    st.header("Fire Behavior")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # Fire behavior distribution
        fire_behavior = report['Fire Behavior'].value_counts().reset_index()
        fig5 = px.pie(fire_behavior, values='count', names='Fire Behavior', title='Distribution of Fire Behaviors')
        st.plotly_chart(fig5)

    with col2:
        # All specific fire behaviors
        specific_behavior = report['Fire Behavior (More Specific)'].value_counts().reset_index()
        fig6 = px.bar(specific_behavior, x='Fire Behavior (More Specific)', y='count', title='Specific Fire Behaviors')
        st.plotly_chart(fig6)

    with col3:
        # List top 5 (or fewer) specific fire behaviors
        top_items = specific_behavior.head(5)
        st.write(f"Top {len(top_items)} Specific Fire Behavior{'s' if len(top_items) > 1 else ''}:")
        for i, (behavior, count) in enumerate(zip(top_items['Fire Behavior (More Specific)'], top_items['count']), 1):
            st.write(f"{i}. {behavior}: {count}")
    return top_items

def fuels_tab(report):
    st.header("Fuels")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # Primary fuel model distribution
        primary_fuel = report['Primary Fuel Model'].value_counts().reset_index()
        fig7 = px.pie(primary_fuel, values='count', names='Primary Fuel Model', title='Primary Fuel Models')
        st.plotly_chart(fig7)

    with col2:
        # List top 5 (or fewer) primary fuel models
        primary_top_items = primary_fuel.head(5)
        st.write(f"Top {len(primary_top_items)} Primary Fuel Model{'s' if len(primary_top_items) > 1 else ''}:")
        for i, (fuel, count) in enumerate(zip(primary_top_items['Primary Fuel Model'], primary_top_items['count']), 1):
            st.write(f"{i}. {fuel}: {count}")

    with col3:
        # Secondary fuel model distribution
        secondary_fuel = report['Secondary Fuel Model'].value_counts().reset_index()
        fig8 = px.pie(secondary_fuel, values='count', names='Secondary Fuel Model', title='Secondary Fuel Models')
        st.plotly_chart(fig8)

    with col4:
        # List top 5 (or fewer) secondary fuel models
        secondary_top_items = secondary_fuel.head(5)
        st.write(f"Top {len(secondary_top_items)} Secondary Fuel Model{'s' if len(secondary_top_items) > 1 else ''}:")
        for i, (fuel, count) in enumerate(zip(secondary_top_items['Secondary Fuel Model'], secondary_top_items['count']), 1):
            st.write(f"{i}. {fuel}: {count}")
    return [primary_top_items, secondary_top_items]