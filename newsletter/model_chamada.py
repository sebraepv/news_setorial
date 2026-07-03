from openai import OpenAI
import os

from dotenv import load_dotenv

load_dotenv('variaveis.env')

endpoint = os.getenv("ENDPOINT_KIMI")
deployment_name = "Kimi-K2.6"
api_key = os.getenv("KIMI_API_KEY_FOUNDRY")

client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

completion = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
)

print(completion.choices[0].message)