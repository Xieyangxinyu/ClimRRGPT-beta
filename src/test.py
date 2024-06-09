from pygris.geocode import geolookup
from census import Census
import geopandas as gpd
import streamlit as st
import pydeck as pdk
import pandas as pd

c = Census("93c3297165ad8b5b6c81e0ed9e2e44a38e56224f")


lon = -76.4946333
lat = 39.0343178



geocode = geolookup(longitude = lon, latitude= lat)['GEOID'][0]
state_code = geocode[0:2]
county_code = geocode[2:5]
tract_code = geocode[5:11]

state_tract = gpd.read_file(f"./data/tl_2022_us_county/tl_2022_us_county.shp")
state_tract = state_tract.to_crs(epsg=4326)
state_tract["GEOID"] = state_tract["GEOID"].astype(str)

# C17002_001E: count of ratio of income to poverty in the past 12 months (total)
# C17002_002E: count of ratio of income to poverty in the past 12 months (< 0.50)
# C17002_003E: count of ratio of income to poverty in the past 12 months (0.50 - 0.99)
# B01003_001E: total population

tract = c.acs5.state_county(fields = ('NAME', 'C17002_001E', 'C17002_002E', 'C17002_003E', 'B01003_001E'),
        state_fips = state_code,
        county_fips = county_code,
        year = 2022)

tract_df = pd.DataFrame(tract)


tract_df["GEOID"] = tract_df["state"] + tract_df["county"]
tract_df["GEOID"] = tract_df["GEOID"].astype(str)
print(tract_df)
tract_df = state_tract.merge(tract_df, on = "GEOID")
print(tract_df)


print(tract_df.geometry.is_valid)

layer = pdk.Layer(
    'GeoJsonLayer',
    tract_df,
    opacity=0.8,
    stroked=False,
    filled=True,
    extruded=True,
    wireframe=True,
    get_fill_color=[255, 0, 0, 140],
)

# Set the viewport location
view_state = pdk.ViewState(
    latitude=lat,
    longitude=lon,
    zoom=11,
    pitch=50

)

# Render the map
r = pdk.Deck(layers=[layer], initial_view_state=view_state)
st.pydeck_chart(r)