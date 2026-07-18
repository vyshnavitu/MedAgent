from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv(""GROQ_API_KEY""))

def get_llm_response(messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # updated model
        messages=messages,
        temperature=0.4,
        max_tokens=1024,
    )
    return response.choices[0].message.content