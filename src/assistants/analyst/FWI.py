import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import plotly.graph_objects as go
from src.assistants.analyst.utils import get_pinned_map

def initialize_data():
    grid_cells_gdf = gpd.read_file('./data/GridCellsShapefile/GridCells.shp')
    grid_cells_crs = grid_cells_gdf.crs
    wildfire_df = pd.read_csv('./data/FireWeatherIndex_Wildfire.csv')
    return grid_cells_gdf, grid_cells_crs, wildfire_df

def retrieve_crossmodels_within_radius(lat, lon, grid_cells_gdf, grid_cells_crs):
    '''
    Retrieves all Crossmodel indices within a specified radius of a given latitude and longitude.
    
    Parameters:
    - lat: Latitude of the location.
    - lon: Longitude of the location.
    - radius_km: The radius in kilometers around the point to retrieve Crossmodel indices.
    - grid_cells_gdf: GeoDataFrame of the grid cells.
    - grid_cells_crs: Coordinate Reference System (CRS) of the grid cells.
    
    Returns:
    - A list containing the Crossmodel indices for the grid cells within the specified radius.
    '''
    # Convert the radius in kilometers to meters (as most CRS use meters)
    radius_meters = 36 * 1000

    # Create a point from the given latitude and longitude
    point = Point(lon, lat)
    point_gseries = gpd.GeoSeries([point], crs="EPSG:4326")  # Assume input is in WGS84

    # Transform the point to match the grid cell CRS
    point_transformed = point_gseries.to_crs(grid_cells_crs)

    # Create a buffer around the point in the correct CRS
    buffer = point_transformed.buffer(radius_meters)
    buffer = buffer.to_crs(grid_cells_crs)

    # Find grid cells that intersect the buffer area
    intersecting_cells = grid_cells_gdf[grid_cells_gdf.intersects(buffer.geometry[0])]

    # Retrieve the Crossmodel indices from the intersecting cells
    crossmodel_indices = intersecting_cells['Crossmodel'].tolist()

    with open('./chat_history/crossmodels.txt', 'w') as f:
        for item in crossmodel_indices:
            f.write("%s\n" % item)
    
    return crossmodel_indices

def get_wildfire_index(wildfire_df, cross_model):
    wildfire_index = wildfire_df[wildfire_df['Crossmodel'] == cross_model].iloc[0]
    return wildfire_index

def extract_fwi_values_to_dataframe(wildfire_indices):
    """
    Extracts and organizes the FWI values for specific seasons and time periods into a pandas DataFrame,
    focusing only on the specified FWI values to reduce computational complexity.
    
    Parameters:
    - wildfire_indices: Dictionary containing the FWI for each Crossmodel, as obtained from FWI_retrieval function.
    
    Returns:
    - A pandas DataFrame containing the FWI values for each season and time period across all indices, filtered based on specified FWI values.
    """
    # Define the FWI values of interest
    fwi_values_all = [
        'wildfire_spring_Hist', 'wildfire_spring_Midc', 'wildfire_spring_Endc', 
        'wildfire_summer_Hist', 'wildfire_summer_Midc', 'wildfire_summer_Endc',
        'wildfire_autumn_Hist', 'wildfire_autumn_Midc', 'wildfire_autumn_Endc',
        'wildfire_winter_Hist', 'wildfire_winter_Midc', 'wildfire_winter_Endc'
    ]

    # Initialize a list to hold all rows for the DataFrame
    data_rows = []

    # Columns for the resulting DataFrame
    columns = ['Crossmodel'] + fwi_values_all
    
    # Iterate over each Crossmodel entry in the wildfire_indices
    for cross_model, index_values in wildfire_indices.items():
        # Start with the Crossmodel identifier
        fwi_values = [cross_model]
        
        # Append the FWI values for the specified FWI values
        fwi_values += [index_values[key] for key in fwi_values_all]
        
        # Add the collected FWI values to the data rows
        data_rows.append(fwi_values)

    # Create a DataFrame from the aggregated data rows
    fwi_df = pd.DataFrame(data_rows, columns=columns)
    
    return fwi_df


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

def categorize_fwi_color(value):
    """Categorize the FWI value into its corresponding class."""
    try:
        if pd.isnull(value):
            return '#808080'  # Gray for NaN FWI values
        elif value <= 9:
            return '#FFFF00'  # Yellow for Low
        elif value <= 21:
            return '#FFCC00'  # Light Orange for Medium
        elif value <= 34:
            return '#FF9900'  # Orange for High
        elif value <= 39:
            return '#FF6600'  # Dark Orange for Very High
        elif value <= 53:
            return '#FF3300'  # Red-Orange for Extreme
        else:
            return '#FF0000'  # Red for Very Extreme
    except Exception as e:
        return '#808080'  # Gray as fallback for any unexpected values or types


def FWI_retrieval(lat, lon):
    '''
    Retrieves the Fire Weather Index (FWI) for all locations within a specified radius of a given latitude and longitude.
    
    Parameters:
    - lat: Latitude of the central location.
    - lon: Longitude of the central location.
    - radius_km: The radius in kilometers to search for grid cells around the central location.
    
    Returns:
    - A dictionary containing the FWI for each Crossmodel within the specified radius.
    '''
    grid_cells_gdf, grid_cells_crs, wildfire_df = initialize_data()

    maps = get_pinned_map(lat, lon)

    
    # Assuming retrieve_crossmodels_within_radius is already defined
    cross_models = retrieve_crossmodels_within_radius(lat, lon, grid_cells_gdf, grid_cells_crs)
    
    # Dictionary to hold the wildfire index for each cross model
    wildfire_indices = {}
    
    for cross_model in cross_models:
        wildfire_index = get_wildfire_index(wildfire_df, cross_model)
        wildfire_indices[cross_model] = wildfire_index

    fwi_df = extract_fwi_values_to_dataframe(wildfire_indices)
    wildfire_index = fwi_df.iloc[:, 1:].mean()
    wildfire_sd = fwi_df.iloc[:, 1:].std()

    # only keep the data in 2 decimal places
    wildfire_index = {key: round(value, 2) for key, value in wildfire_index.items()}
    wildfire_sd = {key: round(value, 2) for key, value in wildfire_sd.items()}

    # write a for loop for the output
    output = f"The Fire Weather Index (FWI) for location (lat: {lat}, lon: {lon}) is, reported within a 36 km radius. Historically (1995 - 2004), the FWI is"
    for key, value in wildfire_index.items():
        if key.endswith("Hist"):
            output += f"{key}: {value}({categorize_fwi(value)}, standard error: {wildfire_sd[key]}), "
    output = output[:-2] + ". In the mid-century (2045 - 2054), the FWI is projected to be"
    for key, value in wildfire_index.items():
        if key.endswith("Midc"):
            output += f"{key}: {value}({categorize_fwi(value)}), "
    output = output[:-2] + ". In the end-of-century (2085 - 2094), the FWI is projected to be"
    for key, value in wildfire_index.items():
        if key.endswith("Endc"):
            output += f"{key}: {value}({categorize_fwi(value)}), "
    output = output[:-2] + "."

    
    ## Visualizations
    categories = ['Historical(1995 - 2004)', 'Mid-Century(2045 - 2054)', 'End-of-Century(2085 - 2094)']

    fwi_values_with_categories = [[] for _ in range(4)]
    for key, value in wildfire_index.items():
        if 'spring' in key:
            fwi_values_with_categories[0].append(f"{value} (se: {wildfire_sd[key]}) {categorize_fwi(value)}")
        elif 'summer' in key:
            fwi_values_with_categories[1].append(f"{value} (se: {wildfire_sd[key]}) {categorize_fwi(value)}")
        elif 'autumn' in key:
            fwi_values_with_categories[2].append(f"{value} (se: {wildfire_sd[key]}) {categorize_fwi(value)}")
        elif 'winter' in key:
            fwi_values_with_categories[3].append(f"{value} (se: {wildfire_sd[key]}) {categorize_fwi(value)}")
    
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
    fig.update_layout(title=f'Fire Weather Index (FWI) Data for Location (lat: {lat}, lon: {lon}) with standard error')
   

    fig2 = go.Figure(data=[go.Table(
    header=dict(values=['FWI Class', 'FWI Values in Class'],
                fill_color='paleturquoise',
                align='left', font=dict(color='black', size=14)),
    cells=dict(values=[data['FWI Class'], data['FWI Values in Class']],
               fill_color='lavender',
               align='left',font=dict(color='black', size=14)))
    ])
    fig2.update_layout(height=380)

    return output, maps, [fig, fig2]

if __name__ == "__main__":
    print(FWI_retrieval(37.8044, -122.2711))