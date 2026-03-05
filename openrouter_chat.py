import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def chat(prompt: str) -> str:
    response = client.chat.completions.create(
        model="qwen/qwen3-32b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello."
    print(chat(prompt))
