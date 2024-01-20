from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI()

# read model from .env file
model = os.getenv("OPENAI_MODEL")


def checklist_of_questions(messages, context):
    
    messages = messages + [{"role": "system", "content": "List 3 clarifying questions you can ask the user.\n**Only output the list of questions.**"}]
    
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    return response.choices[0].message.content
