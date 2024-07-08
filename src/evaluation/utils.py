import re
import ast

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


def parse_tool_file(content, interactions):
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
        type_value = 'literature' if 'title:' in tool_outputs.lower() else 'values_and_recommendations'
        #print(f"{PURPLE}tool_outputs{ENDC}", tool_outputs, f"{PURPLE}type{ENDC}", type_value, f"{PURPLE}llm_response{ENDC}", llm_response)
        # Find previous user query that matches the first sentence of the llm_response
        first_sentence = llm_response.split('\n')[1].strip()
        previous_query = find_previous_user_query(interactions, first_sentence)
        #print(f"{PURPLE}previous_query{ENDC}", previous_query)

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


def parse_user_profile(content):
    # Initialize an empty dictionary
    user_profile = {}

    # Split the data into lines
    lines = content.split("\n")

    # Iterate over each line
    for line in lines:
        if ":" in line:  # Check if the line contains a key-value pair
            # Split the line into key and value based on the first colon
            key, value = line.split(":", 1)

            # Clean up the key and value
            key = key.strip().strip('*- ').replace("**", "").lower()  # Remove extra characters and make lowercase
            value = value.replace("**", "").strip()

            # Add the key-value pair to the dictionary
            user_profile[key] = value

    return user_profile


def convert_scores(input_data):
    # Check if input_data is a string that could represent a list
    if isinstance(input_data, str) and input_data.strip().startswith('[') and input_data.strip().endswith(']'):
        input_data = ast.literal_eval(input_data)  # Convert string representation of list to actual list

    match = re.match(r"(\d+)/(\d+)", input_data)
    if match is not None:
        errors, total = map(int, match.groups())
        return total-errors, total, 0

    else:
        score_map = {'Yes': 2, 'Could be better': 1, 'No': 0}
        total_score = 0
        total_count = 0
        count_na = 0

        for i, response in enumerate(input_data):
            if len(input_data) == 2:
                # Is there any new factual information? Is there any contradictory information?
                response = 'No' if response == 'Yes' else 'Yes'
            elif len(input_data) == 3:
                if i == 0 or i == 2: # Does my response contain too many jargons? Does my response contain redundant or useless information?
                    response = 'No' if response == 'Yes' else 'Yes'

            if response != 'Not Applicable':
                total_score += score_map.get(response, 0)
                total_count += 1
            else:
                count_na += 1

        return total_score, total_count, count_na
    
if __name__ == '__main__':
    filepath = 'Beaverton_mitigation_policy/user_profile.txt'
    with open(filepath, 'r') as file:
        user_profile = file.read()
    
    user_profile_dict = parse_user_profile(user_profile)
    print(user_profile_dict)