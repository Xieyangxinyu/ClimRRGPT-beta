from openai import OpenAI
import json
from wildfire_index_retrieval import wildfire_index_retrieval
from literature import literature_search
from dotenv import load_dotenv
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
    messages = [message] + messages
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
                            "description": "The query to search for. For example, 'What is the relationship between climate change and wildfire?'",
                        },
                    },
                    "required": ["query"],
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
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        # Step 2: check if the model wanted to call a function
        if tool_calls:
            # Step 3: call the function
            # Note: the JSON response may not always be valid; be sure to handle errors
            available_functions = {
                "wildfire_index_retrieval": wildfire_index_retrieval,
                "literature_search": literature_search
            }  # only one function in this example, but you can have multiple
            messages.append(response_message)  # extend conversation with assistant's reply
            # Step 4: send the info for each function call and function response to the model
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                if function_to_call == wildfire_index_retrieval:
                    function_response = function_to_call(
                        lat=function_args.get("lat"),
                        lon=function_args.get("lon"),
                    )
                elif function_to_call == literature_search:
                    function_response = function_to_call(
                        query=function_args.get("query"),
                    )
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )
                if function_to_call == literature_search:
                    messages.append(
                        {
                            "role": "system",
                            "content": "For each paper that you plan to include in your answer, be sure to cite this paper with the in-text APA style. Also include a 'References' section at the end of your answer.\n**Example**:\nThe smoke and air pollution from wildfires can harm crops and livestock, impacting overall agricultural production in the area (Caldararo, 2015).\n\n References:\nCaldararo, N. (2015). Wildfire and Fire-adapted Ecology: How People Created the Current Fire Disasters.\n",
                        }
                    )
                elif function_to_call == wildfire_index_retrieval:
                    messages.append(
                        {
                            "role": "system",
                            "content": "When you answer the user's question, remember to report and interpret the exact Fire Weather Index (FWI) numbers. FWI values in excess of 20 typically represent high levels of fire danger, with levels above 30 representing very high to potentially extreme levels of fire danger.\n",
                        }
                    )
            return messages
        return response_message.content
    except Exception as e:
        return messages


import streamlit as st

st.title("Wildfire GPT")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        messages = run_conversation(
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
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
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    #print(st.session_state.messages)