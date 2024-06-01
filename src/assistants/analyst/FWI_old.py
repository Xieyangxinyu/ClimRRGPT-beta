import geopandas as gpd
from plotly.subplots import make_subplots
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

def categorize_fwi(value):
    """Categorize the FWI value into its corresponding class and return the value and category."""
    if value <= 9:
        return 'Low'
    elif value <= 21:
        return 'Medium'
    elif value <= 34:
        return 'High'
    elif value <= 39:
        return 'Very High'
    elif value <= 53:
        return 'Extreme'
    else:
        return 'Very Extreme'

def fire_weather_index(lat, lon):
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
    
    ## Visualizations
    
    categories = ['Historical(1995 - 2004)', 'Mid-Century(2045 - 2054)', 'End-of-Century(2085 - 2094)']
    fwi_values_all = [
        [wildfire_index['wildfire_spring_Hist'], wildfire_index["wildfire_spring_Midc"], wildfire_index["wildfire_spring_Endc"]],
        [wildfire_index['wildfire_summer_Hist'], wildfire_index["wildfire_summer_Midc"], wildfire_index["wildfire_summer_Endc"]],
        [wildfire_index['wildfire_autumn_Hist'], wildfire_index["wildfire_autumn_Midc"], wildfire_index["wildfire_autumn_Endc"]],
        [wildfire_index['wildfire_winter_Hist'], wildfire_index["wildfire_winter_Midc"], wildfire_index["wildfire_winter_Endc"]]
    ]
    fwi_values = [[round(value, 2) for value in sublist] for sublist in fwi_values_all]

    # Combine each FWI value with its category
    fwi_values_with_categories = [[(value, categorize_fwi(value)) for value in sublist] for sublist in fwi_values]

    data = {
    'FWI Class': ['Low', 'Medium', 'High', 'Very High', 'Extreme', 'Very Extreme'],
    'FWI Values in Class': ['0-9 FWI', '9-21 FWI', '21-34 FWI', '34-39 FWI', '39-53 FWI', 'Above 53 FWI']
    }

    

    fig = go.Figure(data=[go.Table(
    header=dict(
        values=['Category', 'Spring', 'Summer', 'Autumn', 'Winter'],
        fill_color='royalblue',  # Header background color
        align='left',
        font=dict(color='white', size=14)  # Header text color and size
    ),
    cells=dict(
        values=[categories] + fwi_values_with_categories,
        fill_color=['paleturquoise', 'lavender'],  # Cell background colors
        align='left',
        font=dict(color='black', size=14)  # Cell text color and size
    )
    )])     
    # Add title
    fig.update_layout(height=400)
    fig.update_layout(title=f'Fire Weather Index (FWI) Data for Location (lat: {lat}, lon: {lon})')
   

    fig2 = go.Figure(data=[go.Table(
    header=dict(values=['FWI Class', 'FWI Values in Class'],
                fill_color='paleturquoise',
                align='left', font=dict(color='black', size=14)),
    cells=dict(values=[data['FWI Class'], data['FWI Values in Class']],
               fill_color='lavender',
               align='left',font=dict(color='black', size=14)))
    ])
    fig2.update_layout(height=380)

    '''
    
    # Load your DataFrame
    df = pd.read_csv('./data/CCSM_2004_1995_crossmodel.csv', usecols=[cross_model])

    # Clip negative values
    df = df.clip(lower=0)

    # Group by day of the year
    grouped = df.groupby(df.index % 365)

    # Calculate statistics
    statistics = grouped[cross_model].agg(['median', 'min', 'max'])

    # Create a Plotly figure
    ts = go.Figure()

    # Add Mean line
    ts.add_trace(go.Scatter(x=statistics.index, y=statistics['median'], mode='lines', name='Median', line=dict(color='red')))
    # Add Max line
    ts.add_trace(go.Scatter(x=statistics.index, y=statistics['max'], mode='lines', name='Max', line=dict(dash='dash', color='purple')))
    # Add Min line
    ts.add_trace(go.Scatter(x=statistics.index, y=statistics['min'], mode='lines', name='Min', line=dict(dash='dash', color='orange')))
    # Update layout
    ts.update_layout(
        title='Historical Fire Weather Index(FWI) (1995-2004) for Each Day of the Year',
        xaxis_title='Day of the Year',
        yaxis_title='FWI',
        legend_title='Statistics'
    )

    # save the figure as a pickle object
    # pickle.dump([fig, ts], open("temp", "wb"))
    # pickle.dump([ts], open("temp", "wb"))
    # with open("temp", "wb") as file:
    #     pickle.dump(ts, file)
    '''

    return output, [fig, fig2]

if __name__ == "__main__":
    print(fire_weather_index(37.8044, -122.2711))