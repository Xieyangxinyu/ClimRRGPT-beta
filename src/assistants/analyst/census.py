from pygris.geocode import geolookup
from census import Census
import geopandas as gpd
import pydeck as pdk
import plotly.graph_objects as go
import pandas as pd
c = Census("93c3297165ad8b5b6c81e0ed9e2e44a38e56224f")
state_county = gpd.read_file(f"./data/tl_2022_us_county/tl_2022_us_county.shp")
state_county = state_county.to_crs(epsg=4326)
state_county["GEOID"] = state_county["GEOID"].astype(str)

def get_census_info(lon: float, lat: float) -> str:
    
    geocode = geolookup(longitude=lon, latitude=lat)['GEOID'][0]
    state_code = geocode[0:2]
    county_code = geocode[2:5]

    # C17002_001E: count of ratio of income to poverty in the past 12 months (total)
    # C17002_002E: count of ratio of income to poverty in the past 12 months (< 0.50)
    # C17002_003E: count of ratio of income to poverty in the past 12 months (0.50 - 0.99)
    # B01003_001E: total population
    # B25001_001E: Housing units
    # B19013_001E: Median household income
    # B27001_001E: Health insurance coverage

    county = c.acs5.state_county(fields = ('NAME', 'C17002_001E', 'C17002_002E', 'C17002_003E', 'B01003_001E', 'B25001_001E', 'B19013_001E', 'B27001_001E'),
            state_fips = state_code,
            county_fips = county_code,
            year = 2022)

    output = f"In 2022, the total population in {county[0]['NAME']} is {county[0]['B01003_001E']}. The number of individual under the poverty line is {county[0]['C17002_001E']}. In particular, {county[0]['C17002_002E']} individuals hold income less than half of what is considered the minimum required to meet basic living expenses. There are {county[0]['B25001_001E']} housing units in the area. The median household income is {county[0]['B19013_001E']}. The number of individuals with health insurance coverage is {county[0]['B27001_001E']}."

    county_df = pd.DataFrame(county)
    county_df["GEOID"] = county_df["state"] + county_df["county"]
    county_df["GEOID"] = county_df["GEOID"].astype(str)
    county_df = state_county.merge(county_df, on = "GEOID")

    layer = pdk.Layer(
        'GeoJsonLayer',
        county_df,
        opacity=0.8,
        stroked=False,
        filled=True,
        extruded=True,
        wireframe=True,
        get_fill_color=[255, 0, 0, 140],
    )
    view_state = pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=11,
        pitch=50
        )
    maps = pdk.Deck(layers=[layer], initial_view_state=view_state)

    # draw a table with the data

    fig = go.Figure(data=[go.Table(
        header=dict(values=['Population', 'Below Poverty', 'Below Half Poverty', 'Median Household Income', 'Health Insurance Coverage', 'Housing Units'],
                        fill_color='royalblue',  # Header background color
                        align='left',
                        font=dict(color='white', size=14)),
        cells=dict(values=[county_df['B01003_001E'], county_df['C17002_001E'], county_df['C17002_002E'], county_df['B19013_001E'], county_df['B27001_001E'], county_df['B25001_001E']],
                        fill_color=['paleturquoise', 'lavender'],  # Cell background colors
                        align='left',
                        font=dict(color='black', size=14)))
        ])
    
    fig.update_layout(title=f'Census Data for County {county[0]["NAME"]} surrounding location (lat: {lat}, lon: {lon})')

    return output, maps, [fig]