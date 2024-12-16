import streamlit as st
import os
from PIL import Image
from st_pages import add_page_title

add_page_title(layout="wide")

# Set the directory containing images
image_dir = "temp_images"

# Get a sorted list of image file paths
image_files = sorted([f for f in os.listdir(image_dir) if f.endswith('.png')], 
                     key=lambda x: int(x.split('_')[1].split('.')[0]))

# Title
st.title("Sliding Slideshow for Timestep Images")

# Slider to select the timestep
timestep = st.slider("Select Timestep", 
                     min_value=1, 
                     max_value=len(image_files), 
                     step=1, 
                     value=1)

# Load and display the selected image
col1, col2, col3 = st.columns(3)
with col1:
    image_path = os.path.join(image_dir, f"timestep_{timestep}.png")
    if os.path.exists(image_path):
        image = Image.open(image_path)
        st.image(image, caption=f"Timestep {timestep}", use_column_width=True)
    else:
        st.write("Image not found.")
with col2:
    image_path = os.path.join(image_dir, f"timestep_{timestep}.png")
    if os.path.exists(image_path):
        image = Image.open(image_path)
        st.image(image, caption=f"Timestep {timestep}", use_column_width=True)
    else:
        st.write("Image not found.")
with col3:
    image_path = os.path.join(image_dir, f"timestep_{timestep}.png")
    if os.path.exists(image_path):
        image = Image.open(image_path)
        st.image(image, caption=f"Timestep {timestep}", use_column_width=True)
    else:
        st.write("Image not found.")