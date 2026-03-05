import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def chat(messages: list, tools: list = None) -> dict:
    kwargs = dict(model="qwen/qwen3-32b", messages=messages, temperature=0.7)
    if tools:
        kwargs["tools"] = tools
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello."
    msg = chat([{"role": "user", "content": prompt}])
    print(msg.content)
