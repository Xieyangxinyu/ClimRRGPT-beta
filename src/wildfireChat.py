from openai import OpenAI
import json
from wildfire_index_retrieval import wildfire_index_retrieval
from literature import literature_search
from fire_history import find_closest_fire_histories_within_50_miles
from dotenv import load_dotenv
from checklist import checklist_of_questions
import os

load_dotenv()

client = OpenAI()

# read template from file
with open("prompt/prompt.txt", "r") as f:
    template = f.read()

# read model from .env file
model = os.getenv("OPENAI_MODEL")

def run_conversation(messages):
    
    message = {
        "role": "system",
        "content": template
    }
    messages = [message] + messages + [{"role": "system", "content": "Respond to the user's question. Think about if you need to ask clarifying questions first. Limit your response to at most 3 sentences."}]

    tools = [{
            "type": "function",
            "function": {
                "name": "wildfire_index_retrieval",
                "description": "Get the Fire Weather Index (FWI) for a given latitude and longitude.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lat": {
                            "type": "number",
                            "description": "The latitude of the location",
                        },
                        "lon": {
                            "type": "number",
                            "description": "The longitude of the location",
                        },
                    },
                    "required": ["lat", "lon"],
                },
            },
    },
        {
            "type": "function",
            "function": {
                "name": "literature_search",
                "description": "Get the title and abstract of 5 papers possibly related to wildfire for a given query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search for based on the user's project. For example, 'How can wildfire impact the bridge construction in Santa Monica given climate change?'",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "find_closest_fire_histories_within_50_miles",
                "description": "Get the 3 closest fire history records to a given latitude and longitude within 50 miles.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lat": {
                            "type": "number",
                            "description": "The latitude of the location",
                        },
                        "lon": {
                            "type": "number",
                            "description": "The longitude of the location",
                        },
                    },
                    "required": ["lat", "lon"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "checklist_of_questions",
                "description": "Get a checklist of 5 questions by offering a brief description of the context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "context": {
                            "type": "string",
                            "description": "As an expert in offering wildfire related recommendations to the user, create a checklist of 5 questions to understand the user's projects and needs. Here is an example: \n- location\n- timeline\n- scale\n",
                        }
                    },
                    "required": ["context"],
                },
            },
        }
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",  # auto is default, but we'll be explicit
        )
        print(response.choices[0].message)
        messages = messages[:-1]
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        # Step 2: check if the model wanted to call a function
        if tool_calls:
            # Step 3: call the function
            # Note: the JSON response may not always be valid; be sure to handle errors
            available_functions = {
                "wildfire_index_retrieval": wildfire_index_retrieval,
                "literature_search": literature_search,
                "find_closest_fire_histories_within_50_miles": find_closest_fire_histories_within_50_miles,
                "checklist_of_questions": checklist_of_questions,
            }  # only one function in this example, but you can have multiple
            messages.append(response_message)  # extend conversation with assistant's reply
            # Step 4: send the info for each function call and function response to the model
            for tool_call in tool_calls:
                try:
                    function_name = tool_call.function.name
                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    print(function_name)
                    print(function_to_call)
                    print(function_args)
                    if function_to_call == wildfire_index_retrieval:
                        function_response = function_to_call(
                            lat=function_args.get("lat"),
                            lon=function_args.get("lon"),
                        ) + "\nThis data is extracted from the Climate Risk & Resilience Portal (ClimRR), developed by the Center for Climate Resilience and Decision Science (CCRDS) at Argonne National Laboratory. You can access the website:https://disgeoportal.egs.anl.gov/ClimRR/\nThe Fire Weather Index (FWI) estimates wildfire danger using weather conditions that influence the spread of wildfires. The FWI is comprised of multiple components that are developed using daily readings of temperature, relative humidity, wind speed, and 24-hour precipitation. This weather information is used to estimate the total fuel available for combustion (dry organic material) and the rate of fire spread. The FWI is useful for evaluating weather-based conditions that heighten the danger of wildfire spread once ignition has occurred; it does not account for sources of ignition, which can have both natural and human causes. The FWI ranges from zero to infinity, with higher numbers corresponding to greater fire danger. The level of wildfire danger, as represented by FWI, varies based on regional characteristics, such as a region’s typical level of fire danger and its land cover. For example, areas in the U.S. Southwest, which are often exceptionally dry, will have higher average daily FWI values than areas in the Northeast. Values above 25 typically represent a high level of danger in the northern regions, whereas values above 40-45 often represent a high level of danger in the Southwest.  A representative example of fire danger classes used by the European Forest Fire Information System can be found here [https://effis.jrc.ec.europa.eu/about-effis/technical-background/fire-danger-forecast].\n----------\n\n**When you answer the user's question, remember to report and interpret the exact Fire Weather Index (FWI) numbers, as well as to offer the user link to the data source.**\n"
                    elif function_to_call == literature_search:
                        function_response = function_to_call(
                            query=function_args.get("query"),
                        ) + "\n----------\n\nFor each paper that you plan to include in your answer, be sure to cite this paper with the in-text APA style. Also include a 'References' section at the end of your answer.\n**Example**:\nThe smoke and air pollution from wildfires can harm crops and livestock, impacting overall agricultural production in the area (Caldararo, 2015).\n\n References:\nCaldararo, N. (2015). Wildfire and Fire-adapted Ecology: How People Created the Current Fire Disasters. doi:http://doi.org/10.2139/ssrn.2649620\n"
                    elif function_to_call == find_closest_fire_histories_within_50_miles:
                        function_response = function_to_call(
                            lat=function_args.get("lat"),
                            lon=function_args.get("lon"),
                        )
                        if function_response == "No fire history records found within 50 miles.":
                            function_response += " This only means that we do not find research data from NOAA’s fire history and paleoclimate services."
                        else:
                            function_response += "\n----------\nThis data is extracted from the International Multiproxy Paleofire Database (IMPD), an archive of fire history data derived from natural proxies such as tree scars and charcoal and sediment records. You can access the website: https://www.ncei.noaa.gov/products/paleoclimatology/fire-history\n----------\n\nDiscuss the research about the fire history of these sites and make sure to include all the links to data and metadata. Also include a 'References' section at the end of your answer.\n\n**Example**:\nA study by Guiterman et al. (2015) used dendroecological methods (tree-ring analysis) to reconstruct a high-severity fire that occurred in 1993 in a ponderosa pine-dominated forest. The historical fire regime (1625-1871) at this site was characterized by frequent, low-severity fires, usually in dry years following wet years. Notably, fires ceased after 1871, coinciding with increased livestock grazing in the region.\n\n References:\nGuiterman et al., (2015), Dendroecological methods for reconstructing high-severity fire in pine-oak forests, Tree-Ring Research, 71(2), 67-77, 10.3959/1536-1098-71.2.67\n"
                    elif function_to_call == checklist_of_questions:
                        function_response = function_to_call(
                            messages=messages[:-1], context = function_args.get("context")
                        ) + "\n----------\n\nPlease make sure to ask all the questions in the checklist. Only ask one question at a time.\n"
                    print(function_response)
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )
                except Exception as e:
                    print(e)
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": "Sorry, I couldn't find any information about that. Please try again.",
                        }
                    )
            messages.append({"role": "system", "content": "Give a concise and professional response."})
            return messages
        return response_message.content
    except Exception as e:
        print(e)
        return messages


import streamlit as st

st.title("Wildfire GPT")

import clipboard


def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

if "copied" not in st.session_state: 
    st.session_state.copied = []

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hi, I'm Wildfire GPT, your specialized assistant for managing and understanding wildfire-related issues. Whether you're a homeowner, a community leader, or simply someone seeking to learn more about wildfire trends and safety, I'm here to provide you with detailed information and advice. You can ask me to analyze wildfire trends at your specific location, access historical fire data nearby, or get recommendations on how to mitigate the impact of wildfires. Let's work together to enhance your awareness and preparedness. "})
    first_message = client.chat.completions.create(
        model=model,
        messages=[{"role": "assistant", "content": "Hi, I'm Wildfire GPT, your specialized assistant for managing and understanding wildfire-related issues. Whether you're a homeowner, a community leader, or simply someone seeking to learn more about wildfire trends and safety, I'm here to provide you with detailed information and advice. You can ask me to analyze wildfire trends at your specific location, access historical fire data nearby, or get recommendations on how to mitigate the impact of wildfires. Let's work together to enhance your awareness and preparedness. "}, {"role": "system", "content": "Ask the user one question about their background to get to know them. Limit your response to 1 sentence."}],
        temperature=1,
    ).choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": first_message})
    st.session_state.openAI_messages = []

index = 0
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            st.button("📋", on_click=on_copy_click, args=(message["content"],), key=index)
            index += 1

if prompt := st.chat_input("Ask me anything?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.openAI_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        messages = run_conversation(
            messages=st.session_state.openAI_messages
        )
        if type(messages) == str:
            full_response = messages
        else:
            for response in client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            ):
                full_response += (response.choices[0].delta.content or "")
                message_placeholder.markdown(full_response + "▌")
            st.session_state.openAI_messages = messages[:-1]
            
        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.session_state.openAI_messages.append({"role": "assistant", "content": full_response})

    st.rerun()
