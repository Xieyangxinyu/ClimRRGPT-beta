import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd

@st.cache_data
def get_perimeters_data():
    perimeters = gpd.read_file('./data/WFIGS_Interagency_Perimeters/Perimeters.shp')
    perimeters = perimeters[perimeters['attr_Inc_4'] == 'WF']
    return perimeters

def analyze_wildfire_perimeters():
    st.title("Wildfire Perimeters")
    st.write("[Source](https://data-nifc.opendata.arcgis.com/datasets/nifc::wfigs-interagency-fire-perimeters/about)")

    perimeters = get_perimeters_data()
    st.title("Wildfire Perimeters")
    st.write("[Source](https://data-nifc.opendata.arcgis.com/datasets/nifc::wfigs-interagency-fire-perimeters/about)")
    cross_model = st.session_state.crossmodel

    col1, col2 = st.columns(2)
    perimeters = perimeters.to_crs(cross_model.crs)
    perimeters = gpd.sjoin(perimeters, cross_model, how="inner", predicate='intersects')
    report = perimeters[['attr_Inc_2', 'poly_GISAc', 'attr_FireC', 'attr_Fir_7', 'attr_Conta', 'attr_Contr', 'geometry']]
    # drop duplicates
    report = report.drop_duplicates()
    # if the control date is smaller than the discovery date, set the control date None
    
    report.loc[pd.to_datetime(report['attr_Conta']) < pd.to_datetime(report['attr_Fir_7']), 'attr_Conta'] = None
    report.loc[pd.to_datetime(report['attr_Contr']) < pd.to_datetime(report['attr_Fir_7']), 'attr_Contr'] = None
    m5 = folium.Map(location=st.session_state.lat_long, zoom_start=st.session_state.zoom)
    fg = folium.FeatureGroup(name="Perimeters")
    fg.add_child(
        folium.features.GeoJson(report, tooltip = folium.features.GeoJsonTooltip(fields=['attr_Inc_2', 'poly_GISAc', 'attr_FireC', 'attr_Fir_7', 'attr_Conta', 'attr_Contr'], aliases=['Incident Name', 'Incident Acres', 'Fire Cause', 'Fire Discovery Date', 'Containment Date', 'Control Date']),
                                style_function=lambda x: {'fillColor': 'red', 'color': 'red'})
    )
    with col1:
        st_folium(m5, feature_group_to_add=fg, width=450, height=450)
    with col2:
        report = report[['attr_Inc_2', 'poly_GISAc', 'attr_FireC', 'attr_Fir_7', 'attr_Conta', 'attr_Contr']]
        report = report.rename(columns={'attr_Inc_2': 'Incident Name', 'poly_GISAc': 'Incident Acres', 'attr_FireC': 'Fire Cause', 'attr_Fir_7': 'Fire Discovery Date', 'attr_Conta': 'Containment Date', 'attr_Contr': 'Control Date'})
        # sort by the Fire Discovery Date
        report = report.sort_values(by='Fire Discovery Date', ascending=True)
        report = report.reset_index(drop=True)
        st.dataframe(report, hide_index=True)
    
    col1, col2 = st.columns(2)
    with col1:
        report['year'] = pd.to_datetime(report['Fire Discovery Date']).dt.year.astype(str)
        # plot the number of incidents per year using line plot
        table = report.groupby('year')['Incident Name'].count().reset_index()
        table = table.rename(columns={'Incident Name': 'Total Incident Count'})
        st.line_chart(table.set_index('year'), y='Total Incident Count', use_container_width=True)
    with col2:
        # plot the acres burned per year
        report['Incident Acres'] = report['Incident Acres'].astype(float)
        table = report.groupby('year')['Incident Acres'].sum().reset_index()
        table = table.rename(columns={'Incident Acres': 'Total Acres Burned'})
        st.line_chart(table.set_index('year'), y='Total Acres Burned', use_container_width=True)