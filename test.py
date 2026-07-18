from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


response = client.chat.completions.create(
    model="llama-3.1-8b-instant",   # ✅ latest working model
    messages=[
        {"role": "system", "content": "You are a helpful medical AI assistant."},
        {"role": "user", "content": "Say hello"}
    ]
)

print(response.choices[0].message.content)