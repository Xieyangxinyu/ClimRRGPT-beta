import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import pickle
import plotly.graph_objects as go

def initialize_data():
    grid_cells_gdf = gpd.read_file('./data/GridCellsShapefile/GridCells.shp')
    grid_cells_crs = grid_cells_gdf.crs
    wildfire_df = pd.read_csv('./data/FireWeatherIndex_Wildfire.csv')
    return grid_cells_gdf, grid_cells_crs, wildfire_df

def get_crossmodel(lat, lon, grid_cells_gdf, grid_cells_crs):
    '''
    input: 
        lat: latitude of the location
        lon: longitude of the location
        grid_cells_gdf: GeoDataFrame of the grid cells
        grid_cells_crs: CRS of the grid cells
    '''
    # Re-creating the point with the correct coordinates and setting its CRS to match the grid cells CRS
    point_corrected_crs = Point(lon, lat)
    point_corrected_crs = gpd.GeoSeries([point_corrected_crs], crs="EPSG:4326")
    point_corrected_crs = point_corrected_crs.to_crs(grid_cells_crs)
    cross_model = grid_cells_gdf[grid_cells_gdf.contains(point_corrected_crs.iloc[0])]['Crossmodel'].reset_index(drop=True)[0]
    #print(cross_model)
    return cross_model

def get_wildfire_index(wildfire_df, cross_model):
    wildfire_index = wildfire_df[wildfire_df['Crossmodel'] == cross_model].iloc[0]
    return wildfire_index

def FWI_retrieval(lat, lon, messages=None):
    '''
    input:
        lat: latitude of the location
        lon: longitude of the location
    output:
        a string containing the Fire Weather Index (FWI) for a given latitude and longitude.
    '''
    grid_cells_gdf, grid_cells_crs, wildfire_df = initialize_data()
    cross_model = get_crossmodel(lat, lon, grid_cells_gdf, grid_cells_crs)
    wildfire_index = get_wildfire_index(wildfire_df, cross_model)

    output = f"Historically (1995 - 2004), the Fire Weather Index (FWI) for location (lat: {lat}, lon: {lon}) is {wildfire_index['wildfire_spring_Hist']} in spring, {wildfire_index['wildfire_summer_Hist']} in summer, {wildfire_index['wildfire_autumn_Hist']} in autumn, and {wildfire_index['wildfire_winter_Hist']} in winter. In the mid-century (2045 - 2054), the FWI is projected to be {wildfire_index['wildfire_spring_Midc']} in spring, {wildfire_index['wildfire_summer_Midc']} in summer, {wildfire_index['wildfire_autumn_Midc']} in autumn, and {wildfire_index['wildfire_winter_Midc']} in winter. In the end-of-century (2085 - 2094), the FWI is projected to be {wildfire_index['wildfire_spring_Endc']} in spring, {wildfire_index['wildfire_summer_Endc']} in summer, {wildfire_index['wildfire_autumn_Endc']} in autumn and {wildfire_index['wildfire_winter_Endc']} in winter."
    categories = ['Historically(1995 - 2004)', 'Mid-Century(2045 - 2054)', 'End-of-Century(2085 - 2094)']
    fwi_values = [
        [wildfire_index['wildfire_spring_Hist'], wildfire_index["wildfire_spring_Midc"], wildfire_index["wildfire_spring_Endc"]],
        [wildfire_index['wildfire_summer_Hist'], wildfire_index["wildfire_summer_Midc"], wildfire_index["wildfire_summer_Endc"]],
        [wildfire_index['wildfire_autumn_Hist'], wildfire_index["wildfire_autumn_Midc"], wildfire_index["wildfire_autumn_Endc"]],
        [wildfire_index['wildfire_winter_Hist'], wildfire_index["wildfire_winter_Midc"], wildfire_index["wildfire_winter_Endc"]]
    ]
    fig = go.Figure(data=[go.Table(
            header=dict(values=['Category', 'Spring', 'Summer', 'Autumn', 'Winter']),
            cells=dict(values=[categories] + fwi_values)
            )])

    # Add title
    fig.update_layout(title=f'Fire Weather Index (FWI) Data for Location (lat: {lat}, lon: {lon})')
    
    # save the figure as a pickle object
    pickle.dump(fig, open("temp", "wb"))

    return output

if __name__ == "__main__":
    print(FWI_retrieval(37.8044, -122.2711))