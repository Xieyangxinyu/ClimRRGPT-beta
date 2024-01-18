from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI()

# read model from .env file
model = os.getenv("OPENAI_MODEL")


def checklist_of_questions(messages, context):
    
    messages = messages + [{"role": "system", "content": context}]
    
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    return response.choices[0].message.content
