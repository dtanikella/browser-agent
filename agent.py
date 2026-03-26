import sys
import json
import time
from datetime import datetime
from openrouter_chat import chat
from browser_actions import TOOLS, TOOL_MAP

MAX_ITERATIONS = 20
STUCK_THRESHOLD = 3  # consecutive all-error iterations before aborting early
WINDOW_SIZE = 5
NEVER_MASK = {"get_current_url", "navigate"}


def mask_tool_result(content: str, tool_name: str) -> str:
    if tool_name == "extract_links":
        texts = [line.split("(")[0].replace("Link:", "").strip()
                 for line in content.splitlines() if line.startswith("Link:")]
        summary = ", ".join(texts[:5]) or "links"
        return f"[result masked: extracted links to {summary}]"
    elif tool_name == "get_page_content":
        return f"[result masked: {content[:80]}...]"
    elif tool_name == "get_page_html":
        return "[result masked: HTML snapshot]"
    elif tool_name == "take_screenshot":
        return "[result masked: screenshot]"
    elif tool_name in ("click", "type_text", "press_key", "wait_for_selector"):
        return "[result masked: action completed]"
    return "[result masked]"


def build_working_messages(raw_history: list, static_prefix: list) -> list:
    result = list(static_prefix)
    max_idx = len(raw_history) - 1
    for msg in raw_history:
        age = max_idx - msg.get("_turn_index", 0)
        tool_name = msg.get("_tool_name")
        clean = {k: v for k, v in msg.items() if not k.startswith("_")}
        if msg["role"] == "tool" and tool_name not in NEVER_MASK and age > WINDOW_SIZE:
            clean = {**clean, "content": mask_tool_result(msg["content"], tool_name)}
        result.append(clean)
    return result


def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


SYSTEM_PROMPT = (
    "You are a browser agent. You have access to browser tools to navigate and interact with websites. "
    "You will be given a URL to start at and a goal. Navigate step by step, calling tools as needed. "
    "When you have gathered enough information to answer the goal, stop calling tools and give your final answer. "
    "Be systematic: navigate, observe the page (use extract_links to find links, get_page_content for text, and go_back if you reach a dead end), interact with inputs, wait for results, read the output."
)


def run(url: str, goal: str):
    static_prefix = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Start at: {url}\nGoal: {goal}"},
    ]
    raw_history = []

    consecutive_all_error_iterations = 0

    for iteration in range(MAX_ITERATIONS):
        working = build_working_messages(raw_history, static_prefix)
        response = chat(working, tools=TOOLS)

        if not response.tool_calls:
            print(response.content)
            return

        assistant_msg = {"role": "assistant", "content": response.content, "_turn_index": len(raw_history)}
        if response.tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in response.tool_calls
            ]
        raw_history.append(assistant_msg)

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
            result_str = str(result)
            tool_results.append(result_str)
            raw_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str,
                "_turn_index": len(raw_history),
                "_tool_name": fn_name,
            })

        if all(r.startswith("ERROR:") for r in tool_results):
            consecutive_all_error_iterations += 1
        else:
            consecutive_all_error_iterations = 0

        if consecutive_all_error_iterations >= STUCK_THRESHOLD:
            print(f"{ts()} [agent] stuck after {STUCK_THRESHOLD} consecutive all-error iterations, aborting")
            break

    print(f"{ts()} [agent] requesting final synthesis (no tools)")
    working = build_working_messages(raw_history, static_prefix)
    final = chat(working)
    print(final.content)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python agent.py <url> \"<goal>\"")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
