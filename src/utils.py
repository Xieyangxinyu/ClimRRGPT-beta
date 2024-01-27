from src.config import client, model
import json
import yaml

def load_config(path):
    """
    This function loads the config file.
    """
    with open(path, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config

def populate_tools(config):
    """
    This function populates the tools dictionary with the functions
    defined in the config file.
    """
    tools = []
    for tool_name, tool_meta_data in config["available_functions"].items():
        tool = {}
        tool["type"] = "function"
        tool["function"] = {}
        tool["function"]["name"] = tool_name
        tool["function"]["description"] = tool_meta_data["description"]
        tool["function"]["parameters"] = {}
        tool["function"]["parameters"]["type"] = "object"
        tool["function"]["parameters"]["properties"] = {}
        if tool_meta_data["parameters"]:
            for param_name, param_meta_data in tool_meta_data["parameters"].items():
                param = {}
                param["type"] = param_meta_data["type"]
                param["description"] = param_meta_data["description"]
                tool["function"]["parameters"]["properties"][param_name] = param
        tool["function"]["parameters"]["required"] = tool_meta_data["required"]
        tools.append(tool)
    return tools


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

def get_openai_response(messages, temperature = None, tools = None):
     
    if temperature:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
    elif tools:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        
    return response.choices[0].message.content

def run_conversation(messages, tools, available_functions, config):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    messages.pop()
    response_message = response.choices[0].message
    #print(response_message)
    if response_message.tool_calls:
        response_message.tool_calls = response_message.tool_calls[:1]
        tool_calls = response_message.tool_calls
        messages.append(response_message)
        for tool_call in tool_calls:
            try:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                function_response = function_to_call(**function_args)
                if config["available_functions"][function_name]["appendix"]:
                    path = config["path"] + "appendix/" + config["available_functions"][function_name]["appendix"]
                    function_response = add_appendix(function_response, path)
            except Exception as e:
                print(e)
                function_response = str(e) 
                #function_response = run_conversation(messages[:-1], tools, available_functions, config)
            
            message = {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
            #print(function_response)
            messages.append(message)
        return messages
    
    return response_message.content