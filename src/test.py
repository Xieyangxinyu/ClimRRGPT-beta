import streamlit as st
import pickle
import os

# Function to load session state
def load_state():
    if os.path.exists('state.pkl'):
        with open('state.pkl', 'rb') as f:
            data = pickle.load(f)
            print(data)
            for key, value in data.items():
                st.session_state[key] = value
    else:
        st.warning('No saved state to load. Starting with a new session.')

# Function to save session state
def save_state():
    with open('state.pkl', 'wb') as f:
        states = {}
        for key, value in st.session_state.items():
            states[key] = value
        pickle.dump(states, f)

# Load session state
load_state()

# Initialize counter if not in session state
if 'counter' not in st.session_state:
    st.session_state.counter = 0

# Button to increment the counter
if st.button('Increment'):
    st.session_state.counter += 1

st.write(f'Counter: {st.session_state.counter}')

# Button to save state
if st.button('Save State'):
    save_state()
    st.success('State saved!')

