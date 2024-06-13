address = 'Sangre de Cristo Mountain, New Mexico, USA'
lat, lon = (36.5561017, -105.5280874)


import streamlit as st
from streamlit_folium import st_folium
import folium

def main():
    st.title("Drop a Pin on the Map")
    st.write("Click on the map to select a location.")

    # Create a Folium map object
    m = folium.Map(location=[lat, lon], zoom_start=8)
    folium.Circle(
        location=[lat, lon],
        radius=36000,  # 36km in meters
        color='red',
        fill=True,
        fill_color='red',
        fill_opacity=0.2
    ).add_to(m)

    folium.Marker(location=[lat, lon], popup='Initial Location').add_to(m)
    # Add a click listener to the map
    m.add_child(folium.ClickForMarker(popup='Clicked Location'))
    m.add_child(folium.LatLngPopup())
    map = st_folium(m, height=350, width=700)

    try:
        data = (map['last_clicked']['lat'],map['last_clicked']['lng'])
        m2 = folium.Map(location=[lat, lon], zoom_start=8)
        folium.Marker(location=[lat, lon], popup='Initial Location').add_to(m2)
        folium.Circle(
            location=data,
            radius=36000,  # 36km in meters
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.2
        ).add_to(m2)
        folium.Marker(location=[data[0], data[1]], popup='Initial Location').add_to(m2)
        st_folium(m2, height=350, width=700)
    except:
        data = None
    if data:
        st.write(f"Clicked Coordinates:{data}")
    


if __name__ == "__main__":
    main()