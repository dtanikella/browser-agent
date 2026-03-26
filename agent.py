import sys
import json
import time
from datetime import datetime
from openrouter_chat import chat
from browser_actions import TOOLS, TOOL_MAP

MAX_ITERATIONS = 20
STUCK_THRESHOLD = 3  # consecutive all-error iterations before aborting early


def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


SYSTEM_PROMPT = (
    "You are a browser agent. You have access to browser tools to navigate and interact with websites. "
    "You will be given a URL to start at and a goal. Navigate step by step, calling tools as needed. "
    "When you have gathered enough information to answer the goal, stop calling tools and give your final answer. "
    "Be systematic: navigate, observe the page (use extract_links to find links, get_page_content for text), interact with inputs, wait for results, read the output."
)


def run(url: str, goal: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Start at: {url}\nGoal: {goal}"},
    ]

    consecutive_all_error_iterations = 0

    for iteration in range(MAX_ITERATIONS):
        response = chat(messages, tools=TOOLS)

        if not response.tool_calls:
            print(response.content)
            return

        messages.append(response)

        tool_results = []
        for tool_call in response.tool_calls:
            fn_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            args_str = "  ".join(f"{k}={v}" for k, v in args.items())
            print(f"{ts()} [tool] {fn_name}  {args_str}")
            t0 = time.time()
            result = TOOL_MAP[fn_name](**args)
            elapsed = time.time() - t0
            print(f"{ts()} [tool] {fn_name}  done {elapsed:.2f}s")
            tool_results.append(str(result))
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

        if all(r.startswith("ERROR:") for r in tool_results):
            consecutive_all_error_iterations += 1
        else:
            consecutive_all_error_iterations = 0

        if consecutive_all_error_iterations >= STUCK_THRESHOLD:
            print(f"{ts()} [agent] stuck after {STUCK_THRESHOLD} consecutive all-error iterations, aborting")
            break

    print(f"{ts()} [agent] requesting final synthesis (no tools)")
    final = chat(messages)
    print(final.content)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python agent.py <url> \"<goal>\"")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
