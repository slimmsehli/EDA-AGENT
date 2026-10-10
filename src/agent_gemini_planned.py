#!/usr/bin/env python3
"""Clean single-file terminal AI agent: Gemini model + skills + MCP HTTP tools."""

import time
start_time = time.perf_counter()

import os
import sys
import json
import math
import glob
import re
import socket
import asyncio
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from contextlib import AsyncExitStack

end_time = time.perf_counter()
print(f"Libraries loaded 1 : {end_time - start_time:.6f} seconds")
start_time = time.perf_counter()

from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp import ClientSession
end_time = time.perf_counter()
print(f"Libraries loaded 2 : {end_time - start_time:.6f} seconds")
start_time = time.perf_counter()

try:
    from mcp.client.streamable_http import streamablehttp_client as http_client
except ImportError:
    from mcp.client.streamable_http import streamable_http_client as http_client

end_time = time.perf_counter()
print(f"Libraries loaded 3 : {end_time - start_time:.6f} seconds")
start_time = time.perf_counter()

# --- Terminal colors --------------------------------------------------------
USER, TOOL, ANSWER, DIM, RESET = "\033[94m", "\033[93m", "\033[92m", "\033[90m", "\033[0m"
APPROVE_ALL_TOOLS = False

# --- Project files are resolved from the installation root ------------------
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE, "config", ".env")
load_dotenv(ENV_FILE, override=False)


# --- System prompt + skills -------------------------------------------------
def load_system_prompt():
    prompt_file = os.path.join(BASE, "config", "system_prompt.md")
    prompt = open(prompt_file).read() if os.path.exists(prompt_file) else ""
    for path in sorted(glob.glob(os.path.join(BASE, "skills", "*.md"))):
        prompt += f"\n\n# Skill: {os.path.basename(path)[:-3]}\n" + open(path).read()
    prompt += """

# Plan, act, observe, and revise
For each request that needs tools, create a concise plan with update_plan before acting.
Keep one step in_progress while performing a tool action. After seeing each action's
result, update the plan before taking another action. Use one shell or MCP action per
response so you can observe its result before choosing what to do next. Mark finished
steps completed and revise the remaining steps when needed. Include a brief rationale
in the plan summary, not hidden chain-of-thought. Simple requests that need no tools
do not need a plan.
"""
    return prompt


# --- Conversation and tool logs (stored in the invocation directory) ---------
LOGS_DIR = os.path.join(os.getcwd(), "agent_logs", "planned")
HISTORY_FILE = os.path.join(LOGS_DIR, "history.json")
TOOLS_FILE = os.path.join(LOGS_DIR, "tools.json")
STATS_FILE = os.path.join(LOGS_DIR, "stats.json")
STATS_DEFAULTS = {
    "runs": 0,
    "model_requests": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "usage_unavailable": 0,
    "tool_calls": 0,
    "runtime_seconds": 0.0,
    "last_run_seconds": 0.0,
}


def load_json_log(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as log_file:
        data = json.load(log_file)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}.")
    return data


def load_history():
    return [
        {"role": entry["role"], "content": entry["content"]}
        for entry in load_json_log(HISTORY_FILE)
    ]


def save_history(messages):
    existing_timestamps = {}
    for entry in load_json_log(HISTORY_FILE):
        if "timestamp" in entry:
            key = (entry["role"], entry["content"])
            existing_timestamps.setdefault(key, []).append(entry["timestamp"])

    out = []
    for m in messages:
        role = m["role"] if isinstance(m, dict) else m.role
        content = m["content"] if isinstance(m, dict) else m.content
        if role in ("user", "assistant") and content:
            entry = {"role": role, "content": content}
            timestamps = existing_timestamps.get((role, content), [])
            entry["timestamp"] = (
                timestamps.pop(0) if timestamps else datetime.now().astimezone().isoformat(timespec="seconds")
            )
            out.append(entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as history_file:
        json.dump(out, history_file, indent=2, ensure_ascii=False)


def save_tool_log(tool_log):
    with open(TOOLS_FILE, "w", encoding="utf-8") as tools_file:
        json.dump(tool_log, tools_file, indent=2, ensure_ascii=False)


def load_stats():
    if not os.path.exists(STATS_FILE):
        return STATS_DEFAULTS.copy()
    with open(STATS_FILE, encoding="utf-8") as stats_file:
        saved_stats = json.load(stats_file)
    if not isinstance(saved_stats, dict):
        raise ValueError(f"Expected a JSON object in {STATS_FILE}.")
    stats = STATS_DEFAULTS.copy()
    stats.update(saved_stats)
    for key, default in STATS_DEFAULTS.items():
        value = stats[key]
        valid_type = type(value) in (int, float) if isinstance(default, float) else type(value) is int
        if not valid_type or value < 0 or (isinstance(value, float) and not math.isfinite(value)):
            raise ValueError(f"Invalid non-negative numeric value for '{key}' in {STATS_FILE}.")
    return stats


def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as stats_file:
        json.dump(stats, stats_file, indent=2, ensure_ascii=False)


def get_usage_value(usage, key):
    if isinstance(usage, dict):
        return usage.get(key)
    return getattr(usage, key, None)


# --- Built-in shell tool (needs user confirmation) --------------------------
def run_shell(cmd):
    global APPROVE_ALL_TOOLS
    print(f"\n{TOOL}[shell] {cmd}{RESET}")
    if not APPROVE_ALL_TOOLS:
        choice = input(f"{TOOL}Run this command? [y/N/a=All] {RESET}").strip().lower()
        if choice == "a":
            APPROVE_ALL_TOOLS = True
        elif choice != "y":
            return "User declined to run the command."
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (result.stdout + result.stderr).strip() or "(no output)"


SHELL_TOOL = {
    "type": "function",
    "function": {
        "name": "run_shell",
        "description": "Run a Linux shell command. The user must confirm before it runs.",
        "parameters": {
            "type": "object",
            "properties": {"cmd": {"type": "string", "description": "The command to run."}},
            "required": ["cmd"],
        },
    },
}


PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "update_plan",
        "description": "Create or revise the visible plan for the current user request.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Brief strategy and rationale; do not provide hidden chain-of-thought.",
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed", "blocked"],
                            },
                        },
                        "required": ["title", "status"],
                    },
                },
            },
            "required": ["summary", "steps"],
        },
    },
}


def apply_plan_update(args, plan_state):
    summary = args.get("summary")
    steps = args.get("steps")
    if not isinstance(summary, str) or not summary.strip():
        return "Plan update rejected: summary must be a non-empty string."
    if not isinstance(steps, list) or not steps:
        return "Plan update rejected: steps must be a non-empty array."

    validated_steps = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            return f"Plan update rejected: step {index} must be an object."
        title = step.get("title")
        status = step.get("status")
        if not isinstance(title, str) or not title.strip():
            return f"Plan update rejected: step {index} needs a non-empty title."
        if status not in ("pending", "in_progress", "completed", "blocked"):
            return f"Plan update rejected: step {index} has an invalid status."
        validated_steps.append({"title": title.strip(), "status": status})

    plan_state["summary"] = summary.strip()
    plan_state["steps"] = validated_steps
    print(f"\n{TOOL}[plan] {plan_state['summary']}{RESET}")
    for index, step in enumerate(validated_steps, start=1):
        print(f"{DIM}  {index}. [{step['status']}] {step['title']}{RESET}")
    return "Plan updated."


# --- MCP servers over HTTP ---------------------------------------------------
async def connect_mcp(stack):
    sessions, tools = {}, []
    mcp_file = os.path.join(BASE, "config", "mcp_servers.json")
    if not os.path.exists(mcp_file):
        return sessions, tools
    for name, cfg in json.load(open(mcp_file)).get("servers", {}).items():
        url = urlparse(cfg["url"])
        try:
            with socket.create_connection((url.hostname, url.port or 80), timeout=2):
                pass
        except OSError:
            print(f"{DIM}[mcp] '{name}' not running ({cfg['url']}). Skipping.{RESET}")
            continue
        streams = await stack.enter_async_context(http_client(cfg["url"]))
        read, write = streams[0], streams[1]
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        for tool in (await session.list_tools()).tools:
            full = f"{name}__{tool.name}"
            sessions[full] = (session, tool.name)
            schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
            tools.append({
                "type": "function",
                "function": {
                    "name": full,
                    "description": tool.description or "",
                    "parameters": schema or {"type": "object", "properties": {}},
                },
            })
    return sessions, tools


async def call_tool(name, args, sessions):
    if name == "run_shell":
        return run_shell(args["cmd"])
    session, tool_name = sessions[name]
    result = await session.call_tool(tool_name, args)
    return "\n".join(getattr(c, "text", "") for c in result.content if getattr(c, "text", None)) or "(no output)"


async def print_response_word_by_word(text):
    print(f"\n{ANSWER}", end="")
    for match in re.finditer(r"\S+|\s+", text):
        chunk = match.group()
        sys.stdout.write(chunk)
        sys.stdout.flush()
        if not chunk.isspace():
            await asyncio.sleep(0.05)
    print(RESET)


async def request_with_thinking(request):
    request_task = asyncio.create_task(request)
    dots = 0
    try:
        while not request_task.done():
            dots = dots % 3 + 1
            sys.stdout.write(f"\r{DIM}Thinking{'.' * dots}{RESET}")
            sys.stdout.flush()
            await asyncio.wait({request_task}, timeout=0.4)
        return request_task.result()
    finally:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        if not request_task.done():
            request_task.cancel()
            await asyncio.gather(request_task, return_exceptions=True)


# --- Agent loop -------------------------------------------------------------
async def main():
    run_started_at = time.perf_counter()
    os.makedirs(LOGS_DIR, exist_ok=True)
    stats = load_stats()
    stats["runs"] += 1
    save_stats(stats)
    try:
        await run_agent(stats)
    finally:
        run_duration = time.perf_counter() - run_started_at
        stats["runtime_seconds"] += run_duration
        stats["last_run_seconds"] = run_duration
        save_stats(stats)


async def run_agent(stats):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            f"Set GEMINI_API_KEY in {ENV_FILE} or export it in your environment."
        )
    client = AsyncOpenAI(
        base_url=os.environ.get(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        ),
        api_key=api_key,
    )
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    print(f"{DIM}Using Gemini model: {model}{RESET}")
    print(f"{DIM}Loading system prompt and skills...{RESET}")
    tool_log = load_json_log(TOOLS_FILE)
    print(f"{DIM}Loading conversation history from {HISTORY_FILE}...{RESET}")
    messages = [{"role": "system", "content": load_system_prompt()}] + load_history()
    async with AsyncExitStack() as stack:
        sessions, mcp_tools = await connect_mcp(stack)
        tools = [PLAN_TOOL, SHELL_TOOL] + mcp_tools
        print(f"{DIM}Planned Gemini agent ready with {len(tools)} tools. History: {HISTORY_FILE}. Type 'exit' or 'quit' to leave.{RESET}")
        while True:
            try:
                user = input(f"\n{USER}> {RESET}").strip()
            except EOFError:
                break
            if user.lower() in ("exit", "quit"):
                break
            if not user:
                continue
            messages.append({"role": "user", "content": user})
            save_history(messages)
            plan_state = {"summary": "", "steps": []}
            plan_update_required = False
            while True:
                stats["model_requests"] += 1
                save_stats(stats)
                response = await request_with_thinking(
                    client.chat.completions.create(model=model, messages=messages, tools=tools)
                )
                usage = getattr(response, "usage", None)
                prompt_tokens = get_usage_value(usage, "prompt_tokens") if usage is not None else None
                completion_tokens = get_usage_value(usage, "completion_tokens") if usage is not None else None
                total_tokens = get_usage_value(usage, "total_tokens") if usage is not None else None
                if prompt_tokens is None and completion_tokens is None and total_tokens is None:
                    stats["usage_unavailable"] += 1
                else:
                    for key, value in (
                        ("prompt_tokens", prompt_tokens),
                        ("completion_tokens", completion_tokens),
                    ):
                        if value is not None:
                            if type(value) is not int or value < 0:
                                raise ValueError(f"Invalid {key} value in model response usage: {value!r}")
                            stats[key] += value
                    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
                        total_tokens = prompt_tokens + completion_tokens
                    if total_tokens is not None:
                        if type(total_tokens) is not int or total_tokens < 0:
                            raise ValueError(f"Invalid total_tokens value in model response usage: {total_tokens!r}")
                        stats["total_tokens"] += total_tokens
                save_stats(stats)
                msg = response.choices[0].message
                messages.append(msg)
                if not msg.tool_calls:
                    await print_response_word_by_word(msg.content or "")
                    save_history(messages)
                    break
                action_executed = False
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments or "{}")
                    print(f"{TOOL}[tool] {tc.function.name}({args}){RESET}")
                    stats["tool_calls"] += 1
                    save_stats(stats)
                    try:
                        if tc.function.name == "update_plan":
                            if action_executed:
                                output = "Plan update blocked: first observe the action result in a new response."
                            else:
                                output = apply_plan_update(args, plan_state)
                                if output == "Plan updated.":
                                    plan_update_required = False
                        elif action_executed:
                            output = "Action blocked: only one shell or MCP action is allowed per response. Observe the previous result, update the plan, then retry."
                        elif plan_update_required:
                            output = "Action blocked: update the plan to reflect the previous action before taking another action."
                        elif not plan_state["steps"] or sum(
                            step["status"] == "in_progress" for step in plan_state["steps"]
                        ) != 1:
                            output = "Action blocked: create or update the plan with exactly one in_progress step before using tools."
                        else:
                            output = await call_tool(tc.function.name, args, sessions)
                            action_executed = True
                            plan_update_required = True
                    except Exception as error:
                        tool_log.append({
                            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                            "tool": tc.function.name,
                            "arguments": args,
                            "error": str(error),
                        })
                        save_tool_log(tool_log)
                        raise
                    tool_log.append({
                        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                        "tool": tc.function.name,
                        "arguments": args,
                        "response": output,
                    })
                    save_tool_log(tool_log)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
