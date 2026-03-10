import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def chat(messages: list, tools: list = None) -> dict:
    model = "qwen/qwen3-32b"
    kwargs = dict(model=model, messages=messages, temperature=0.7)
    if tools:
        kwargs["tools"] = tools
    print(f"{ts()} [chat] start  model={model} msgs={len(messages)}")
    t0 = time.time()
    response = client.chat.completions.create(**kwargs)
    print(f"{ts()} [chat] done   {time.time() - t0:.2f}s")
    return response.choices[0].message


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello."
    msg = chat([{"role": "user", "content": prompt}])
    print(msg.content)
