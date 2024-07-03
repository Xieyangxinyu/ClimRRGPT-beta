import re

# Define the ANSI escape sequence for purple
PURPLE = '\033[95m'
ENDC = '\033[0m'  # Reset to default color


def find_previous_user_query(interactions, llm_response_first_sentence):
    last_user_content = None
    for entry in interactions:
        if entry['role'] == 'user':
            last_user_content = entry['content']
        elif entry['role'] == 'assistant' and llm_response_first_sentence in entry['content']:
            return last_user_content
    return None


def parse_file(filepath, interaction_history):
    # Read the entire text file
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()

    # Pattern to find sections with correct delimiter
    sections_pattern = r'\*\*Tool Outputs\*\*(.*?)\*\*LLM Response\*\*(.*?)(?=\*\*Tool Outputs\*\*|$)'

    # Find all matches for the sections
    matches = re.findall(sections_pattern, content, flags=re.DOTALL)

    # Process each match to extract Tool Outputs and LLM Response content
    results = []
    for match in matches:
        tool_outputs = "**Tool Outputs**\n" + match[0].strip()
        llm_response = "**LLM Response**\n" + match[1].strip()

        # Only keep the output with '----------' for evaluation
        if '----------' not in tool_outputs:
            continue  # Skip this pair

        # Separate the Instruction and Tool Outputs
        parts = tool_outputs.split('----------', 1)
        tool_outputs = parts[0].strip()
        # remainder = parts[1].strip()

        # Determine the type based on the presence of 'Title' or 'title'
        type_value = 'literature' if 'title' in tool_outputs.lower() else 'values_and_recommendations'
        print(f"{PURPLE}tool_outputs{ENDC}", tool_outputs, f"{PURPLE}type{ENDC}", type_value, f"{PURPLE}llm_response{ENDC}", llm_response)

        # Find previous user query that matches the first sentence of the llm_response
        previous_query = find_previous_user_query(interactions, first_sentence)
        print(f"{PURPLE}previous_query{ENDC}", previous_query)

        # Initialize dictionary for this pair
        entry = {
            'tool_outputs': tool_outputs,
            'llm_response': llm_response,
            'type': type_value,
            'previous_query': previous_query
        }

        # # Extract instructions if present
        # instructions_match = re.search(r'(# Instructions:|\*\*Instructions\*\*:)(.*?)(?=\*\*LLM Response\*\*|$)', remainder, flags=re.DOTALL)
        # if instructions_match:
        #     # Save the part after '# Instructions:' or '**Instructions**:' and before '**LLM Response**'
        #     entry['instructions'] = instructions_match.group(2).strip()
        #     # print(f"{PURPLE}instructions{ENDC}", instructions_match.group(2).strip())

        results.append(entry)

    # print(results[1])
    return results


def parse_user_profile(data):
    # Initialize an empty dictionary
    user_profile = {}

    # Split the data into lines
    lines = data.split("\n")

    # Iterate over each line
    for line in lines:
        if ":" in line:  # Check if the line contains a key-value pair
            # Split the line into key and value based on the first colon
            key, value = line.split(":", 1)

            # Clean up the key and value
            key = key.strip().strip('*- ').replace("**", "").lower()  # Remove extra characters and make lowercase
            value = value.strip()

            # Add the key-value pair to the dictionary
            user_profile[key] = value

    return user_profile
