from src.utils import run_conversation, load_config, populate_tools
from src.config import client, model
from src.memory.memory import Profile

config = load_config("src/memory/config.yml")
tools = populate_tools(config)

with open("prompt/prompt.md", "r") as f:
    prompt = f.read()

def beginning_messages(user):
    messages = [{"role": "assistant", "content": "Hello! I'm here to assist you with any questions or concerns you may have regarding wildfires. Could you please share with me why you are interested in learning about wildfires? Additionally, is there a specific project or task where wildfires could potentially have an impact on your plans?"},
    {"role": "system", "content": f"Your task is to gather information about the user, i.e. your client, to understand their backgrounds and concerns and get answers for each question in the checklist. {user.summary}\n**Checklist**:{user.checklist}.\n\n Engage the user in conversation by **asking one short question at a time** with emojis. Every single one of your response should include a question. Limit your response to at most 2 sentences. **When you get all the answers, call the checklist_complete function.**"}]
    return messages

def profile_wizard(user, messages):
    available_functions = {
        "checklist_complete": user.checklist_complete,
        "create_plan": user.create_plan,
    }
    messages[:2] = beginning_messages(user)
    user.messages = messages
    response = run_conversation(messages, tools, available_functions, config)
    # if response is a string
    if type(response) == str:
        return response
    if user.initialized and not user.profile_complete:
        messages.pop()
        messages.pop()
        response = client.chat.completions.create(
            model=model,
            messages=beginning_messages(user) + messages[2:],
        ).choices[0].message.content
    elif user.profile_complete:
        response = user.plan
        while len(messages) > 3:
            messages.pop()
        messages[0] = {"role": "system", "content": f"{prompt}"}
        messages[1] = {"role": "assistant", "content": f"User Profile Summary: {user.summary}"}
        messages[2] = {"role": "user", "content": "Tell me about how you plan to assist me!"}
    return response

if __name__ == "__main__":
    user = Profile()
    user.initialized = True
    user.checklist = "1. What specific forested areas in northern Stafford, Kansas are you concerned about with regard to wildfire risk?\n2. Have you noticed any recent changes in climate or vegetation that may impact the wildfire risk in the area?\n3. Are there any specific concerns or vulnerabilities related to your project or property that you would like to address with regards to wildfire risk?"
    system_message = beginning_messages(user)
    messages = system_message + [{"role": "assistant", "content": "Hello! I'm here to assist you with any questions or concerns you may have regarding wildfires. Could you please share with me why you are interested in learning about wildfires? Additionally, is there a specific project or task where wildfires could potentially have an impact on your plans?"},
                                 {"role": "user", "content": "As a civil engineer, I'm interested in understanding the primary factors that contribute to the risk of wildfires in the forested areas of northern Stafford, Kansas. How can we mitigate these risks effectively?"},
                                 {"role": "assistant", "content": "Thank you for sharing your concerns with me. I will do my best to provide you with the information you need. I would like to ask you a few questions to better understand your concerns and how I can help you. What specific forested areas in northern Stafford, Kansas are you concerned about with regard to wildfire risk?"},
                                 {"role": "user", "content": "I'm particularly concerned about the forested areas near Lake Stafford and the surrounding regions in northern Stafford, Kansas. These areas seem to have a higher risk of wildfires, and I'd like to explore strategies to protect them."},
                                {"role": "assistant", "content": "Thank you for sharing your concerns with me. I will do my best to provide you with the information you need. I would like to ask you a few questions to better understand your concerns and how I can help you. Have you noticed any recent changes in climate or vegetation that may impact the wildfire risk in the area?"},
                                {"role": "user", "content": "I'm unsure."},
                                {"role": "assistant", "content": "No problem! Understanding recent changes in climate and vegetation is vital when assessing wildfire risk. Are there any specific concerns or vulnerabilities related to your project or property that you would like to address with regards to wildfire risk?"},
                                {"role": "user", "content": "Yes, I'm specifically interested in how recent climate changes, such as increased temperatures and drought conditions, have impacted the vegetation in the area near Lake Stafford. Understanding these changes will help me assess the wildfire risk and plan accordingly for any projects in the vicinity."},
                                {"role": "assistant", "content": "Thank you for providing that information. It's crucial to consider the impact of climate changes on vegetation and wildfire risk. Additionally, what infrastructure or assets do you want to protect from potential wildfire damage?"},
                                {"role": "user", "content": "I want to protect the infrastructure around Lake Stafford, including recreational facilities, cabins, and any utility infrastructure that may be at risk of wildfire damage. Ensuring their safety is a top priority. Are there any specific environmental or geographical features near Lake Stafford that might influence wildfire behavior, such as terrain or wind patterns?"},
                                {"role": "assistant", "content": "Thank you for sharing that. It's essential to consider the environmental and geographical features that can influence wildfire behavior. Lastly, are you interested in learning about community-wide mitigation strategies or focusing on individual property protection measures?"},
                                {"role": "user", "content": "I'm interested in both community-wide mitigation strategies and individual property protection measures. A comprehensive approach that addresses both aspects would be ideal for safeguarding the area around Lake Stafford from wildfires."},
                                ]

    print(profile_wizard(user, messages))