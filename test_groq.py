import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env
load_dotenv()

# Get Groq API key
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise SystemExit("GROQ_API_KEY .env file mein nahi mili.")

# Create Groq client
client = Groq(api_key=api_key)

print("Connecting to Groq...", flush=True)

try:
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": (
                    "Generate 3 short Python MCQs. "
                    "Give four options and identify the correct answer."
                ),
            }
        ],
        temperature=0.3,
        max_completion_tokens=700,
        timeout=60,
    )

    print("\nAI Quiz Generated Successfully!\n")
    print(response.choices[0].message.content)

except Exception as error:
    print("\nAPI Error:", error)
