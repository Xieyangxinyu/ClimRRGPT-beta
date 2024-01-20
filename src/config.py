from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI()

# read model from .env file
model = os.getenv("OPENAI_MODEL")