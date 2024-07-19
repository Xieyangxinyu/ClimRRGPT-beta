import json
def format_to_json(json_data):
    # Convert the dictionary to a JSON string with indentation
    json_string = json.dumps(json_data, indent=4)
    
    # Wrap the JSON string with ```json and ``` markers
    formatted_string = f"```json\n{json_string}\n```"
    return formatted_string