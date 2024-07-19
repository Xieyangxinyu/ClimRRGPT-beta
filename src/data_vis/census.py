import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd
from census import Census
from src.utils import load_config
from branca.colormap import linear


def safe_sum(series):
    # if the entire series is null, return null
    if series.isnull().all():
        return None
    return series.sum(skipna=True)

def safe_mean(series):
    # if the entire series is null, return null
    if series.isnull().all():
        return None
    return series.mean(skipna=True)

def format_value(value, format_spec):
    if pd.isna(value):
        return "Data not available"
    try:
        return format_spec.format(value)
    except ValueError:
        return str(value)
    
# Function to safely calculate and format rates
def format_rate(series, total_series=None):
    if total_series is not None:
        rate = safe_sum(series) / safe_sum(total_series)
    else:
        rate = safe_mean(series)
    return f"{rate:.2%}" if pd.notnull(rate) else "Data not available"

@st.cache_data
def get_state_bg(state_code):
    return gpd.read_file(f"https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_{state_code}_bg.zip")

@st.cache_data
def get_us_states():
    return gpd.read_file(f"https://www2.census.gov/geo/tiger/TIGER2022/STATE/tl_2022_us_state.zip")

def analyze_census_data(cross_model):
    st.title("Census Data")
    c = Census("93c3297165ad8b5b6c81e0ed9e2e44a38e56224f")

    # Get all state-level census tracts that cross_model is intersecting
    all_states = get_us_states()
    all_states = all_states.to_crs(crs=cross_model.crs)
    intersecting_states = gpd.sjoin(all_states, cross_model, how="inner", predicate='intersects')
    state_codes = intersecting_states['STATEFP'].unique()

    # Initialize an empty list to store dataframes for each state
    state_dfs = []

    acs5_fields = (
        'B01003_001E',  # Total population
        'B25001_001E',  # Total housing units
        'B19013_001E',  # Median household income
        'B25024_002E', 'B25024_003E',  # 1-unit detached and attached structures
        'B25034_010E', 'B25034_011E',  # Structures built 2010 or later
        'B25040_002E', 'B25040_003E', 'B25040_004E',  # House heating fuel (gas, electricity, fuel oil)
        'B01001_020E', 'B01001_021E', 'B01001_022E', 'B01001_023E', 'B01001_024E', 'B01001_025E',  # Population 65 years and over
        'B18101_004E', 'B18101_007E', 'B18101_010E', 'B18101_023E', 'B18101_026E', 'B18101_029E',  # Disability status for 65 years and over
        'B16004_001E', 'B16004_003E',  # English speaking ability
        'B08201_002E',  # No vehicle available
        'B28002_004E', 'B28002_012E',  # Broadband internet and cellular data plan
        'C17002_002E', 'C17002_003E'  # Poverty count
    )

    for state_code in state_codes:
        # Get state tracts
        state_tract = get_state_bg(state_code)
        state_tract = state_tract.to_crs(crs=cross_model.crs)
        state_tract["GEOID"] = state_tract["GEOID"].astype(str)
        
        # Intersect with the cross_model
        state_tract = gpd.sjoin(state_tract, cross_model, how="inner", predicate='intersects')
        state_tract = state_tract[['GEOID', 'geometry']].drop_duplicates()

        # Extract all blockgroup level acs5 data for the current state
        block_groups = c.acs5.state_county_blockgroup(
            fields = acs5_fields,
            state_fips = state_code,
            county_fips = '*',
            tract = '*',
            blockgroup = "*",
            year = 2022
        )
        bg_df = pd.DataFrame(block_groups)

        bg_df["GEOID"] = bg_df["state"] + bg_df["county"] + bg_df["tract"] + bg_df["block group"]
        bg_df["GEOID"] = bg_df["GEOID"].astype(str)
        bg_df = state_tract.merge(bg_df, on = "GEOID")

        state_dfs.append(bg_df)

    # Combine all state dataframes
    combined_bg_df = pd.concat(state_dfs, ignore_index=True)
    combined_bg_df['poverty_count'] = combined_bg_df['C17002_002E'] + combined_bg_df['C17002_003E'] 
    combined_bg_df['poverty_rate'] = combined_bg_df['poverty_count'] / combined_bg_df['B01003_001E']
    combined_bg_df['poverty_rate'] = combined_bg_df['poverty_rate'].fillna(0)
    combined_bg_df['elderly_population'] = combined_bg_df['B01001_020E'] + combined_bg_df['B01001_021E'] + combined_bg_df['B01001_022E'] + combined_bg_df['B01001_023E'] + combined_bg_df['B01001_024E'] + combined_bg_df['B01001_025E']
    combined_bg_df['elderly_population_rate'] = combined_bg_df['elderly_population'] / combined_bg_df['B01003_001E']
    combined_bg_df['single_unit_housing_rate'] = (combined_bg_df['B25024_002E'] + combined_bg_df['B25024_003E']) / combined_bg_df['B25001_001E']
    combined_bg_df['new_housing_rate'] = (combined_bg_df['B25034_010E'] + combined_bg_df['B25034_011E']) / combined_bg_df['B25001_001E']
    combined_bg_df['no_vehicle_rate'] = combined_bg_df['B08201_002E'] / combined_bg_df['B25001_001E']
    combined_bg_df['internet_access_rate'] = (combined_bg_df['B28002_004E'] + combined_bg_df['B28002_012E']) / combined_bg_df['B25001_001E']


    # combined_bg_df['B19013_001E'] is null if set to -666666666
    combined_bg_df['B19013_001E'] = combined_bg_df['B19013_001E'].replace(-666666666, pd.NA)
    
    st.write("## Key Metrics")
    metrics_df = combined_bg_df[['GEOID', 'B01003_001E', 'poverty_count', 'poverty_rate', 'B25001_001E', 'elderly_population_rate', 
                                    'single_unit_housing_rate', 'new_housing_rate', 
                                    'no_vehicle_rate', 'internet_access_rate', 'B19013_001E']]
    
    rename_dict = {
        'B01003_001E': 'Total Population',
        'poverty_count': 'Poverty Count',
        'poverty_rate': 'Poverty Rate',
        'B25001_001E': 'Total Housing Units',
        'elderly_population_rate': 'Elderly Population Rate',
        'single_unit_housing_rate': 'Single Unit Housing Rate',
        'new_housing_rate': 'New Housing Rate',
        'no_vehicle_rate': 'No Vehicle Rate',
        'internet_access_rate': 'Internet Access Rate',
        'B19013_001E': 'Median Household Income'
    }

    metrics_df = metrics_df.rename(columns=rename_dict)
    
    st.dataframe(metrics_df, hide_index=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        # choose a column to display
        options = metrics_df.columns
        # remove the GEOID and any columns with entirely null values
        options = [option for option in options if option != 'GEOID' and not metrics_df[option].isnull().all()]
        metrics_df_with_geometry = combined_bg_df[['GEOID', 'geometry']].merge(metrics_df, on='GEOID')
        selected_column = st.selectbox("Select a column to display", options)
        st.write(f"## {selected_column}")
        m6 = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        # Rest of the function remains the same, just replace bg_df with combined_bg_df
        color_scale = linear.YlOrRd_09.scale(metrics_df[selected_column].min(skipna=True), metrics_df[selected_column].max(skipna=True))

        m6.add_child(
            # color based on selected column
            folium.features.GeoJson(metrics_df_with_geometry, tooltip = folium.features.GeoJsonTooltip(fields=['GEOID', selected_column], aliases=['GEOID', selected_column]),
            style_function=lambda x: {
                'fillColor': color_scale(metrics_df[metrics_df['GEOID'] == x['properties']['GEOID']][selected_column].values[0]),
                'color': 'black',  # Boundary color
                'weight': 1,  # Boundary weight
                'fillOpacity': 0.7
            },)
        )
        # add legend
        m6.add_child(color_scale)
        st_folium(m6, width=450, height=450)
    with col2:
        st.write("**Regional Summary**")

        # Calculate total population and housing units
        total_population = safe_sum(combined_bg_df['B01003_001E'])
        total_housing_units = safe_sum(combined_bg_df['B25001_001E'])
        total_poverty_rate = combined_bg_df['poverty_count'].sum() / total_population
        total_poverty_rate = combined_bg_df['poverty_count'].sum() / total_population
        elderly_population_rate = combined_bg_df['elderly_population'].sum() / total_population
        single_unit_housing_rate = (combined_bg_df['B25024_002E'].sum() + combined_bg_df['B25024_003E'].sum()) / total_housing_units
        new_housing_rate = (combined_bg_df['B25034_010E'].sum() + combined_bg_df['B25034_011E'].sum()) / total_housing_units
        no_vehicle_rate = combined_bg_df['B08201_002E'].sum() / total_housing_units
        internet_access_rate = (combined_bg_df['B28002_004E'].sum() + combined_bg_df['B28002_012E'].sum()) / total_housing_units


        # Calculate median household income, handling potential missing values
        median_household_income = combined_bg_df['B19013_001E'].median(skipna=True)

        st.write(f"Total Population: {format_value(total_population, '{:,}')}")
        st.write(f"Total Housing Units: {format_value(total_housing_units, '{:,}')}")
        st.write(f"Median Household Income: {format_value(median_household_income, '${:,.2f}')}")
        st.write(f"Total Poverty Rate: {format_value(total_poverty_rate, '{:.2%}')}")
        st.write(f"Elderly Population Rate: {format_value(elderly_population_rate, '{:.2%}')}")
        st.write(f"Single Unit Housing Rate: {format_value(single_unit_housing_rate, '{:.2%}')}")
        st.write(f"New Housing Rate (built 2010 or later): {format_value(new_housing_rate, '{:.2%}')}")
        st.write(f"No Vehicle Available Rate: {format_value(no_vehicle_rate, '{:.2%}')}")
        st.write(f"Internet Access Rate: {format_value(internet_access_rate, '{:.2%}')}")

        # Display missing data information
        missing_data = combined_bg_df[['B01003_001E', 'B25001_001E', 'B19013_001E', 'elderly_population_rate', 
                                    'single_unit_housing_rate', 'new_housing_rate', 'no_vehicle_rate', 'internet_access_rate']].isnull().sum()
        missing_data.rename(index=rename_dict, inplace=True)
        if missing_data.sum() > 0:
            st.write("**Missing Data Information**")
            st.write(missing_data[missing_data > 0])

    prompt_config = load_config("./src/data_vis/census.yml")

    # Format the prompt template with the actual values
    prompt = prompt_config['prompt'].format(
        total_population=format_value(total_population, "{:,}"),
        total_housing_units=format_value(total_housing_units, "{:,}"),
        median_household_income=format_value(median_household_income, "${:,.2f}"),
        total_poverty_rate=format_value(total_poverty_rate, "{:.2%}"),
        elderly_population_rate=format_value(elderly_population_rate, "{:.2%}"),
        single_unit_housing_rate=format_value(single_unit_housing_rate, "{:.2%}"),
        new_housing_rate=format_value(new_housing_rate, "{:.2%}"),
        no_vehicle_rate=format_value(no_vehicle_rate, "{:.2%}"),
        internet_access_rate=format_value(internet_access_rate, "{:.2%}")
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant! Provide some insights from the census data."},
        {"role": "user", "content": prompt},
    ]

    return col3, messages