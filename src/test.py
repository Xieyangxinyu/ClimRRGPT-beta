from pygris.geocode import geolookup
from census import Census
import geopandas as gpd
import streamlit as st
import pydeck as pdk
import pandas as pd
from shapely.geometry import Point

c = Census("93c3297165ad8b5b6c81e0ed9e2e44a38e56224f")


lon = -76.4946333
lat = 39.0343178



geocode = geolookup(longitude = lon, latitude= lat)['GEOID'][0]
state_code = geocode[0:2]
county_code = geocode[2:5]
tract_code = geocode[5:11]
radius_meters = 36 * 1000  # radius in meters

point = Point(lon, lat)
# Create a GeoSeries in geographic coordinates
point_gseries = gpd.GeoSeries([point], crs="EPSG:4326")

# Transform to a projected CRS that uses meters (e.g., World Mercator)
point_transformed = point_gseries.to_crs(epsg=3857)

# Create a buffer around the point in the correct CRS
buffer = point_transformed.buffer(radius_meters)

# Optionally transform back to geographic coordinates to check the result in EPSG:4326
buffer = buffer.to_crs(epsg=4326)

state_tract = gpd.read_file(f"https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_{state_code}_bg.zip")
state_tract = state_tract.to_crs(epsg=4326)
state_tract["GEOID"] = state_tract["GEOID"].astype(str)
print(len(state_tract))
state_tract = state_tract[state_tract.intersects(buffer.geometry[0])]
print(len(state_tract))

block_groups = c.acs5.state_county_blockgroup(fields = ('NAME', 'C17002_001E', 'C17002_002E', 'C17002_003E', 'B01003_001E'),
        state_fips = state_code,
        county_fips = '*',
        tract = '*',
        blockgroup = "*",
        year = 2022)

bg_df = pd.DataFrame(block_groups)


bg_df["GEOID"] = bg_df["state"] + bg_df["county"] + bg_df["tract"] + bg_df["block group"]
bg_df["GEOID"] = bg_df["GEOID"].astype(str)
bg_df = state_tract.merge(bg_df, on = "GEOID")

bg_df = bg_df[["C17002_001E", "C17002_002E", "C17002_003E", "B01003_001E", "geometry"]]

# sum each column to a new dataframe
bg_df_sum = pd.DataFrame(bg_df[["C17002_001E", "C17002_002E", "C17002_003E", "B01003_001E"]].sum()).T

print(bg_df_sum['B01003_001E'][0])

layer = pdk.Layer(
    'GeoJsonLayer',
    bg_df,
    opacity=0.8,
    get_fill_color=[255, 0, 0, 140],  # RGBA color: Red with some transparency
    get_line_color=[255, 0, 0],  # Red outline
    line_width_min_pixels=1,
)

# Define the pin data
pins = [{
    "position": [lon, lat],
    "icon_data": {
        "url": "https://cdn-icons-png.flaticon.com/512/684/684908.png",  # Replace with your icon URL
        "width": 128,
        "height": 128,
        "anchorY": 128
    }
}]

# Convert pin data to DataFrame
df_pins = pd.DataFrame(pins)

icon_layer = pdk.Layer(
        "IconLayer",
        df_pins,
        get_icon='icon_data',
        get_position="position",
        size_scale=15,
        get_size=1,
    )

# Set the viewport location
view_state = pdk.ViewState(
    latitude=lat,
    longitude=lon,
    zoom=8,
    pitch=50
)

# Render the map
r = pdk.Deck(layers=[layer, icon_layer], initial_view_state=view_state)
st.pydeck_chart(r)