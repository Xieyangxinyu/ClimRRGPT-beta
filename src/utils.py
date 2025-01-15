import yaml
import time
import streamlit as st
TEXT_CURSOR = "▕"

def load_config(path):
    """
    This function loads the config file.
    """
    with open(path, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config

def add_appendix(response: str, appendix_path: str):
    """
    This function adds the examples to the response.
    
    Args:
        response (str): The response string.
        appendix_path (str): The path to the appendix markdown file.
    """
    with open(appendix_path, "r") as f:
        appendix = f.read()
    response += appendix
    return response


def create_text_stream(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.05)

def stream_static_text(text):
    stream_text = create_text_stream(text)
    st.write_stream(stream_text)
