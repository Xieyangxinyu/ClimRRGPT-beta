from src.utils import populate_tools, run_conversation, load_config
from src.tools import *
import pickle
from src.memory import Profile, profile_wizard
import clipboard
from config import model, client, chat_history_path

with open("prompt/prompt.md", "r") as f:
    prompt = f.read()


tools_config = load_config("src/tools/config.yml")
tools = populate_tools(tools_config)
available_functions = {
    "LiteratureSearch": literature_search,
    "FWI": FWI_retrieval,
    "history": find_closest_fire_histories_within_50_miles,
    "incident": generate_recent_wildfire_incident_summary_report,
    "checklist": checklist_of_questions,
}

prompts = load_config("src/prompts.yml")

init_message = {"role": prompts['init_message']['role'], "content": prompts['init_message']['content']}
prompt_message =  {"role": "system", "content": f"{prompt}"}
summary_prompt = {"role": prompts['summary_prompt']['role'], "content": prompts['summary_prompt']['content']}

def get_response(user: Profile, messages,):
    if user.profile_complete:
        messages.append({"role": "system", "content": "Respond to the user. Think about if you need to ask clarifying questions. For example, you may want to ask the user for the exact location of interest."})
        response = run_conversation(messages, tools, available_functions, tools_config)
    else:
        response = profile_wizard(user, messages)
    return response

def get_memory_prompt(user: Profile):
    return {"role": "assistant", "content": f"Here is the user's profile: {user.profile}\nHere is my plan to assist the user: {user.plan}."}