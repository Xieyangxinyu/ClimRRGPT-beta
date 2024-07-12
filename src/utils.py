from src.config import client, model
import yaml
import time

def load_config(path):
    """
    This function loads the config file.
    """
    with open(path, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config

def get_assistant(config, initialize_instructions):
        """
        This function returns the assistant id from the config file.
        """
        name = config["name"]
        instructions = initialize_instructions()
        tools = populate_tools(config)
        if tools:
            assistant = client.beta.assistants.create(
                name=name,
                instructions=instructions,
                tools=tools,
                model=model,
                top_p=0.8,
                temperature=0.7,
            )
        else:
            assistant = client.beta.assistants.create(
                name=name,
                instructions=instructions,
                model=model,
                top_p=0.8,
                temperature=0.7,
            )
        #with open(f"{config['path']}", "w") as f:
        #    yaml.dump(config, f)
        return assistant

def populate_tools(config):
    """
    This function populates the tools dictionary with the functions
    defined in the config file.
    """
    tools = []
    if "available_functions" not in config.keys():
        return None
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

def create_thread():
    thread = client.beta.threads.create()
    return thread

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

def get_openai_response(messages, top_p = 0.95):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        top_p=top_p,
    )
        
    return response.choices[0].message.content

def stream_static_text(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)