import sys
import json
import time
from datetime import datetime
from openrouter_chat import chat
from browser_actions import TOOLS, TOOL_MAP


def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

SYSTEM_PROMPT = "You are a browser agent. Use the provided tools, and context you've been given to accomplish the task. be concise."


def run(query: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    response = chat(messages, tools=TOOLS)

    if response.tool_calls:
        messages.append(response)
        for tool_call in response.tool_calls:
            fn_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            args_str = "  ".join(f"{k}={v}" for k, v in args.items())
            print(f"{ts()} [tool] {fn_name}  {args_str}")
            t0 = time.time()
            result = TOOL_MAP[fn_name](**args)
            print(f"{ts()} [tool] {fn_name}  done {time.time() - t0:.2f}s")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
        response = chat(messages)

    print(response.content)


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Say hello."
    run(query)
