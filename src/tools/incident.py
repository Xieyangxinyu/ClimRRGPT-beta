import pandas as pd
import pickle
import plotly.subplots as sp
import plotly.graph_objects as go

def prune_data(source_file = "./data/Wildland_Fire_Incident_Locations.csv"):
    data = pd.read_csv(source_file)
    data = data[["X", "Y", "IncidentTypeCategory", "FireDiscoveryDateTime"]]
    # change DateTime to year, month
    data["FireDiscoveryDateTime"] = pd.to_datetime(data["FireDiscoveryDateTime"])
    data["year"] = data["FireDiscoveryDateTime"].dt.year
    data["month"] = data["FireDiscoveryDateTime"].dt.month
    data = data[data["IncidentTypeCategory"] == "WF"]
    # change X to lon, Y to lat
    data = data[["X", "Y", "year", "month"]]
    data.columns = ["lon", "lat", "year", "month"]
    data.to_csv("./data/Wildland_Fire_Incident_Locations_pruned.csv", index=False)


import pandas as pd
from geopy.distance import geodesic

def extract_historical_fire_data(lat, lon, start_year=2015, end_year=2023, source_file="./data/Wildland_Fire_Incident_Locations_pruned.csv"):
    '''
    Finds all fire incidents within 50 miles (approximately 80.4672 kilometers) of the given latitude and longitude, and within the given time range.
    input:
        lat: latitude of the location
        lon: longitude of the location
        start_year: the start year of the historical data, must be later than 2015; 
        end_year: the end year of the historical data, must be earlier than 2023;
        source_file: the source file of the historical data
    '''

    # check if the input is valid
    if start_year < 2015 or end_year > 2023:
        return "start_year must be later than 2015 and end_year must be earlier than 2023."
    if start_year > end_year:
        return "start_year must be earlier than end_year."

    # Load data
    data = pd.read_csv(source_file)
    
    # Filter data by year
    data = data[(data["year"] >= start_year) & (data["year"] <= end_year)]

    # Convert 50 miles to kilometers
    max_distance_km = 50 * 1.60934  # 50 miles in kilometers

    # Calculate distances
    distances = data.apply(lambda row: geodesic((lat, lon), (row['lat'], row['lon'])).kilometers, axis=1)
    
    # Filter data based on distance
    data = data[distances <= max_distance_km]

    return data

import streamlit as st

def generate_recent_wildfire_incident_summary_report(lat, lon, start_year=2015, end_year=2023, messages=None):
    data = extract_historical_fire_data(lat, lon, start_year, end_year)
    if type(data) == str:
        return data  + " Please try again."
    # Count of incidents per year, sorted by year
    incidents_per_year = data['year'].value_counts().sort_index()

    # Count of incidents per month, sorted by month
    incidents_per_month = data['month'].value_counts().sort_index()
    # Assuming you have two DataFrames incidents_per_year and incidents_per_month

    # Create subplots with two rows and one column
    fig = sp.make_subplots(rows=2, cols=1, shared_xaxes=False, subplot_titles=("Wildfire Incidents per Year", "Wildfire Incidents per Month, Aggregated Across Years"))

    print(incidents_per_year)
    # Add the first line chart to the first subplot
    fig.add_trace(go.Scatter(x=incidents_per_year.index, y=incidents_per_year, mode='lines', name='Yearly Incidents'), row=1, col=1)

    # Add the second line chart to the second subplot
    fig.add_trace(go.Scatter(x=incidents_per_month.index, y=incidents_per_month, mode='lines', name='Monthly Incidents'), row=2, col=1)

    # Update subplot titles and labels
    fig.update_layout(title_text="Wildfire Incidents")
    fig.update_xaxes(title_text="Year", row=1, col=1)
    fig.update_xaxes(title_text="Month", row=2, col=1)

    # Summary of incidents
    summary = f"Incidents per Year:\n{incidents_per_year}\n\nIncidents per Month:\n{incidents_per_month}\n"
    pickle.dump(fig, open("temp", "wb"))

    return summary
    
if __name__ == "__main__":
    #prune_data()
    incidents_nearby = generate_recent_wildfire_incident_summary_report(33.9534, -117.3962, 2016, 2022)
    print(incidents_nearby)