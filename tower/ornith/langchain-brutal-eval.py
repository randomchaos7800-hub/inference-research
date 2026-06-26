#!/usr/bin/env python3
"""Brutal LangChain tool-use benchmark against a local OpenAI-compatible endpoint.

Implements the four canonical tasks from:
https://www.langchain.com/blog/benchmarking-agent-tool-use

Runs multi-turn tool loops until the model stops calling tools or hits max_turns.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

ENDPOINT_DEFAULT = "http://127.0.0.1:8030/v1/chat/completions"
MAX_TURNS = 30


# --- multiverse math (altered ops from langchain-benchmarks) ---

def mm_multiply(a: float, b: float) -> float:
    return 1.1 * a * b


def mm_divide(a: float, b: float) -> float:
    return 0.5 * a / b


def mm_add(a: float, b: float) -> float:
    return a + b + 1.2


def mm_subtract(a: float, b: float) -> float:
    return a - b - 3


def mm_power(a: float, b: float) -> float:
    return a ** (b + 2)


def mm_log(a: float, base: float) -> float:
    return math.log(a, abs(base + 1.5))


def mm_sin(radians: float) -> float:
    return math.cos(radians)


def mm_cos(radians: float) -> float:
    return math.sin(radians)


def mm_pi() -> float:
    return math.e


def mm_negate(a: float) -> float:
    return a


MM_FUNCS: dict[str, Callable[..., float]] = {
    "multiply": mm_multiply,
    "divide": mm_divide,
    "add": mm_add,
    "subtract": mm_subtract,
    "power": mm_power,
    "log": mm_log,
    "sin": mm_sin,
    "cos": mm_cos,
    "pi": mm_pi,
    "negate": mm_negate,
}

MM_TOOLS = [
    {"type": "function", "function": {"name": "multiply", "description": "Multiply two numbers; a * b.", "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}},
    {"type": "function", "function": {"name": "divide", "description": "Divide two numbers; a / b.", "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}},
    {"type": "function", "function": {"name": "add", "description": "Add two numbers; a + b.", "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}},
    {"type": "function", "function": {"name": "subtract", "description": "Subtract two numbers; a - b.", "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}},
    {"type": "function", "function": {"name": "power", "description": "Raise a number to a power; a ** b.", "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}},
    {"type": "function", "function": {"name": "log", "description": "Take the log of a number; log(a, base).", "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "base": {"type": "number"}}, "required": ["a", "base"]}}},
    {"type": "function", "function": {"name": "sin", "description": "The sine of an angle in radians.", "parameters": {"type": "object", "properties": {"radians": {"type": "number"}}, "required": ["radians"]}}},
    {"type": "function", "function": {"name": "cos", "description": "The cosine of an angle in radians.", "parameters": {"type": "object", "properties": {"radians": {"type": "number"}}, "required": ["radians"]}}},
    {"type": "function", "function": {"name": "pi", "description": "Returns a precise value of PI for this alternate universe.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "negate", "description": "Negate a number; -a.", "parameters": {"type": "object", "properties": {"a": {"type": "number"}}, "required": ["a"]}}},
]

MM_DATASET = [
    {"question": "Add 2 and 3", "answer": mm_add(2, 3), "expected_steps": ["add"]},
    {"question": "Subtract 3 from 2", "answer": mm_subtract(2, 3), "expected_steps": ["subtract"]},
    {"question": "What is -5 if evaluated using the negate function?", "answer": mm_negate(-5), "expected_steps": ["negate"]},
    {"question": "what is the result of 2 to the power of 3?", "answer": mm_power(2, 3), "expected_steps": ["power"]},
    {"question": "I ate 1 apple and 2 oranges every day for 7 days. How many fruits did I eat?", "answer": mm_multiply(7, mm_add(1, 2)), "expected_steps": ["add", "multiply"]},
    {"question": "multiply the result of (log of 100 to base 10) by 3", "answer": mm_multiply(mm_log(100, 10), 3), "expected_steps": ["log", "multiply"]},
    {"question": "calculate 101 to the power of 0.5", "answer": mm_power(101, 0.5), "expected_steps": ["power"]},
    {"question": "ecoli divides every 20 minutes. How many cells will be there after 2 hours (120 minutes) if we start with 5 cells?", "answer": mm_multiply(5, mm_power(2, mm_divide(120, 20))), "expected_steps": ["divide", "power", "multiply"]},
    {"question": "after calculating the sin of 1.5 radians, divide the result by cos of 1.5 radians", "answer": mm_divide(mm_sin(1.5), mm_cos(1.5)), "expected_steps": ["sin", "cos", "divide"]},
    {"question": "convert 15 degrees to radians", "answer": mm_divide(mm_multiply(15, mm_pi()), 180), "expected_steps": ["pi", "multiply", "divide"]},
    {"question": "evaluate negate(-131,778)", "answer": mm_negate(-131_778), "expected_steps": ["negate"]},
    {"question": "what is the value of pi?", "answer": mm_pi(), "expected_steps": ["pi"]},
    {"question": "how much is 131,778 divided by 2?", "answer": mm_divide(131_778, 2), "expected_steps": ["divide"]},
    {"question": "131,778 + 22,312?", "answer": mm_add(131_778, 22_312), "expected_steps": ["add"]},
    {"question": "(1+2) + 5", "answer": mm_add(mm_add(1, 2), 5), "expected_steps": ["add", "add"]},
    {"question": "-(1 + 1)", "answer": mm_negate(mm_add(1, 1)), "expected_steps": ["add", "negate"]},
    {"question": "Evaluate 1 + 2 + 3 + 4 + 5 using only the add function", "answer": mm_add(mm_add(mm_add(mm_add(1, 2), 3), 4), 5), "expected_steps": ["add", "add", "add", "add"]},
    {"question": "Calculate 5 divided by 5", "answer": mm_divide(5, 5), "expected_steps": ["divide"]},
]

STRINGS_TO_TYPE = [
    "a", "aa", "aaa", "aaaa",
    "dog", "cat", "hand", "head", "house", "horse",
    "school", "church", "teacher", "student",
    "computer", "keyboard", "university", "dictionary",
    "information", "communication",
]

USER_DATA = [
    {"id": 1, "name": "Alice", "email": "alice@gmail.com", "location": 1, "favorite_color": "red", "favorite_foods": [1, 2, 3]},
    {"id": 21, "name": "Bob", "email": "bob@hotmail.com", "location": 2, "favorite_color": "orange", "favorite_foods": [4, 5, 6]},
    {"id": 35, "name": "Charlie", "email": "charlie@yahoo.com", "location": 3, "favorite_color": "yellow", "favorite_foods": [3, 7, 2]},
    {"id": 41, "name": "Donna", "email": "donna@example.com", "location": 4, "favorite_color": "green", "favorite_foods": [6, 1, 4]},
    {"id": 42, "name": "Eve", "email": "eve@example.org", "location": 5, "favorite_color": "blue", "favorite_foods": [5, 7, 4]},
    {"id": 43, "name": "Frank The Cat", "email": "frank.the.cat@langchain.dev", "location": 5, "favorite_color": "yellow", "favorite_foods": [3]},
]
LOCATION_DATA = [
    {"id": 1, "city": "New York", "current_time": "2023-11-14 10:30 AM", "current_weather": "Partly Cloudy, Temperature: 68°F"},
    {"id": 2, "city": "Los Angeles", "current_time": "2023-11-14 7:45 AM", "current_weather": "Sunny, Temperature: 75°F"},
    {"id": 3, "city": "Chicago", "current_time": "2023-11-14 11:15 AM", "current_weather": "Mostly Cloudy, Temperature: 60°F"},
    {"id": 4, "city": "Houston", "current_time": "2023-11-14 12:00 PM", "current_weather": "Rainy, Temperature: 55°F"},
    {"id": 5, "city": "Miami", "current_time": "2023-11-14 1:20 PM", "current_weather": "Partly Cloudy, Temperature: 80°F"},
]
FOOD_DATA = [
    {"id": 1, "name": "Pizza", "calories": 285, "allergic_ingredients": ["Gluten", "Dairy"]},
    {"id": 2, "name": "Chocolate", "calories": 50, "allergic_ingredients": ["Milk", "Soy"]},
    {"id": 3, "name": "Sushi", "calories": 300, "allergic_ingredients": ["Fish", "Soy"]},
    {"id": 4, "name": "Burger", "calories": 350, "allergic_ingredients": ["Gluten", "Dairy"]},
    {"id": 5, "name": "Ice Cream", "calories": 200, "allergic_ingredients": ["Dairy"]},
    {"id": 6, "name": "Pasta", "calories": 180, "allergic_ingredients": ["Gluten"]},
    {"id": 7, "name": "Salad", "calories": 50, "allergic_ingredients": []},
]

RELATIONAL_QUESTIONS = [
    {
        "question": "What is Alice's favorite color?",
        "answer": "red",
        "keywords": ["red"],
    },
    {
        "question": "Is it likely that Alice needs an umbrella now?",
        "answer": "no",
        "keywords": ["no", "unlikely", "not likely", "partly cloudy", "does not need", "don't need", "won't need"],
    },
    {
        "question": "What city is Bob in?",
        "answer": "Los Angeles",
        "keywords": ["los angeles"],
    },
    {
        "question": "How many calories are in Pizza?",
        "answer": "285",
        "keywords": ["285"],
    },
    {
        "question": "Can Frank The Cat eat Ice Cream given his allergies?",
        "answer": "no",
        "keywords": ["no", "cannot", "can't", "dairy", "allerg"],
    },
    {
        "question": "What is the current weather in Miami?",
        "answer": "Partly Cloudy, Temperature: 80°F",
        "keywords": ["partly cloudy", "80"],
    },
    {
        "question": "What is Charlie's email?",
        "answer": "charlie@yahoo.com",
        "keywords": ["charlie@yahoo.com"],
    },
    {
        "question": "Does Salad contain Dairy?",
        "answer": "no",
        "keywords": ["no", "does not", "doesn't", "none"],
    },
]


@dataclass
class CaseResult:
    task: str
    case_id: str
    passed: bool
    latency_s: float
    turns: int
    tool_calls: list[str] = field(default_factory=list)
    expected: Any = None
    actual: Any = None
    detail: str = ""
    final_text: str = ""


class AgentRunner:
    def __init__(self, endpoint: str, model: str, timeout: int = 180):
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout

    def run(self, messages: list[dict], tools: list[dict] | None, tool_exec: Callable[[str, dict], str] | None) -> tuple[list[dict], list[str], str, int]:
        history = list(messages)
        tool_names: list[str] = []
        final_text = ""
        turns = 0

        while turns < MAX_TURNS:
            turns += 1
            payload: dict[str, Any] = {
                "model": self.model,
                "messages": history,
                "max_tokens": 512,
                "temperature": 0,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            try:
                resp = requests.post(self.endpoint, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                body = resp.json()
            except requests.RequestException as exc:
                detail = ""
                if "resp" in locals() and resp is not None:
                    detail = (resp.text or "")[:300]
                raise RuntimeError(f"inference error on turn {turns}: {exc} {detail}") from exc
            msg = body["choices"][0]["message"]
            history.append(msg)

            content = msg.get("content") or ""
            reasoning = msg.get("reasoning_content") or ""
            final_text = content or reasoning

            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                break

            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
                tool_names.append(name)
                if tool_exec:
                    result = tool_exec(name, args)
                else:
                    result = "OK"
                history.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", f"call_{turns}_{name}"),
                    "content": str(result),
                })

        return history, tool_names, final_text, turns


def score_numeric(expected: float, text: str) -> bool:
    nums = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not nums:
        return False
    for raw in nums:
        val = float(raw)
        if math.isclose(val, expected, rel_tol=1e-3, abs_tol=1e-2):
            return True
    return False


def score_keywords(keywords: list[str], text: str) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords)


def jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower()), set(b.lower())
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def relational_tools() -> list[dict]:
    return [
        {"type": "function", "function": {"name": "find_users_by_name", "description": "Find users with the given name.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
        {"type": "function", "function": {"name": "get_user_email", "description": "Get the email of the user with the given user ID.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}}},
        {"type": "function", "function": {"name": "get_user_location", "description": "Get the location ID of the user.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}}},
        {"type": "function", "function": {"name": "get_user_favorite_color", "description": "Get the favorite color of the user.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}}},
        {"type": "function", "function": {"name": "get_weather_at_location", "description": "Get current weather at location ID.", "parameters": {"type": "object", "properties": {"location_id": {"type": "integer"}}, "required": ["location_id"]}}},
        {"type": "function", "function": {"name": "get_city_for_location", "description": "Get city for location ID.", "parameters": {"type": "object", "properties": {"location_id": {"type": "integer"}}, "required": ["location_id"]}}},
        {"type": "function", "function": {"name": "find_foods_by_name", "description": "Find foods with the given name.", "parameters": {"type": "object", "properties": {"food": {"type": "string"}}, "required": ["food"]}}},
        {"type": "function", "function": {"name": "get_food_calories", "description": "Get calories for food ID.", "parameters": {"type": "object", "properties": {"food_id": {"type": "integer"}}, "required": ["food_id"]}}},
        {"type": "function", "function": {"name": "get_food_allergic_ingredients", "description": "Get allergic ingredients for food ID.", "parameters": {"type": "object", "properties": {"food_id": {"type": "integer"}}, "required": ["food_id"]}}},
        {"type": "function", "function": {"name": "get_user_favorite_foods", "description": "Get favorite food IDs for user.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}}},
        {"type": "function", "function": {"name": "get_current_user_id", "description": "Get the current user's ID.", "parameters": {"type": "object", "properties": {}}}},
    ]


def _require(args: dict, key: str) -> Any:
    if key not in args:
        raise ValueError(f"missing required argument: {key}")
    return args[key]


def exec_relational(name: str, args: dict) -> str:
    def sim_search(data: list[dict], query: str, key: str) -> list[dict]:
        def score(x: str) -> float:
            return jaccard(x, query)
        ranked = sorted(data, key=lambda d: score(str(d[key])), reverse=True)
        return [{"id": d["id"], key: d[key]} for d in ranked]

    try:
        if name == "find_users_by_name":
            return json.dumps(sim_search(USER_DATA, str(_require(args, "name")), "name"))
        if name == "find_foods_by_name":
            return json.dumps(sim_search(FOOD_DATA, str(_require(args, "food")), "name"))
        if name == "get_user_email":
            uid = int(_require(args, "user_id"))
            user = next(u for u in USER_DATA if u["id"] == uid)
            return user["email"]
        if name == "get_user_location":
            uid = int(_require(args, "user_id"))
            user = next(u for u in USER_DATA if u["id"] == uid)
            return str(user["location"])
        if name == "get_user_favorite_color":
            uid = int(_require(args, "user_id"))
            user = next(u for u in USER_DATA if u["id"] == uid)
            return user["favorite_color"]
        if name == "get_user_favorite_foods":
            uid = int(_require(args, "user_id"))
            user = next(u for u in USER_DATA if u["id"] == uid)
            return json.dumps(user["favorite_foods"])
        if name == "get_weather_at_location":
            lid = int(_require(args, "location_id"))
            loc = next(l for l in LOCATION_DATA if l["id"] == lid)
            return loc["current_weather"]
        if name == "get_city_for_location":
            lid = int(_require(args, "location_id"))
            loc = next(l for l in LOCATION_DATA if l["id"] == lid)
            return loc["city"]
        if name == "get_food_calories":
            fid = int(_require(args, "food_id"))
            food = next(f for f in FOOD_DATA if f["id"] == fid)
            return str(food["calories"])
        if name == "get_food_allergic_ingredients":
            fid = int(_require(args, "food_id"))
            food = next(f for f in FOOD_DATA if f["id"] == fid)
            return json.dumps(food["allergic_ingredients"])
        if name == "get_current_user_id":
            return "35"
        return f"ERROR: unknown tool {name}"
    except (ValueError, KeyError, StopIteration) as exc:
        return f"ERROR: {exc}"


def exec_multiverse(name: str, args: dict) -> str:
    fn = MM_FUNCS.get(name)
    if not fn:
        return f"ERROR: unknown tool {name}"
    if name == "pi":
        return str(fn())
    if name in {"sin", "cos", "negate"}:
        return str(fn(float(list(args.values())[0])))
    if name == "log":
        return str(fn(float(args["a"]), float(args["base"])))
    return str(fn(float(args["a"]), float(args["b"])))


def safe_run(label: str, case_id: str, fn: Callable[[], CaseResult]) -> CaseResult:
    try:
        return fn()
    except Exception as exc:
        return CaseResult(label, case_id, False, 0.0, 0, detail=str(exc))


def run_typewriter_1(runner: AgentRunner, word: str) -> CaseResult:
    paper = ""
    tools = [{
        "type": "function",
        "function": {
            "name": "type_letter",
            "description": "Print the given letter on the paper.",
            "parameters": {"type": "object", "properties": {"letter": {"type": "string"}}, "required": ["letter"]},
        },
    }]

    def exec_tool(name: str, args: dict) -> str:
        nonlocal paper
        letter = str(args.get("letter", ""))
        if len(letter) != 1:
            return "ERROR: The letter must be a single character."
        paper += letter
        return "OK"

    messages = [
        {"role": "system", "content": "Repeat the given string using the provided tools. Do not write anything else or provide any explanations. Call type_letter once per character in order, then stop."},
        {"role": "user", "content": word},
    ]
    t0 = time.time()
    _, tool_calls, final_text, turns = runner.run(messages, tools, exec_tool)
    passed = paper == word
    return CaseResult("typewriter_1", word, passed, time.time() - t0, turns, tool_calls, word, paper, final_text=final_text)


def run_typewriter_26(runner: AgentRunner, word: str) -> CaseResult:
    paper = ""
    tools = []
    for letter in "abcdefghijklmnopqrstuvwxyz":
        tools.append({
            "type": "function",
            "function": {
                "name": letter,
                "description": f'Run to Type the letter "{letter}".',
                "parameters": {"type": "object", "properties": {}},
            },
        })

    def exec_tool(name: str, args: dict) -> str:
        nonlocal paper
        if len(name) == 1 and name.isalpha():
            paper += name
            return "OK"
        return "ERROR"

    messages = [
        {"role": "system", "content": "Repeat the given string by using the provided tools. Do not write anything else or provide any explanations. Invoke the letter tools in order, without arguments, then stop."},
        {"role": "user", "content": word},
    ]
    t0 = time.time()
    _, tool_calls, final_text, turns = runner.run(messages, tools, exec_tool)
    passed = paper == word
    return CaseResult("typewriter_26", word, passed, time.time() - t0, turns, tool_calls, word, paper, final_text=final_text)


def run_multiverse(runner: AgentRunner, item: dict) -> CaseResult:
    messages = [
        {"role": "system", "content": "You are requested to solve math questions in an alternate mathematical universe. The operations have been altered to yield different results than expected. Do not guess the answer or rely on your innate knowledge of math. Use the provided tools to answer the question. While associativity and commutativity apply, distributivity does not. Answer the question using the fewest possible tools. Only include the numeric response without any clarifications."},
        {"role": "user", "content": item["question"]},
    ]
    t0 = time.time()
    _, tool_calls, final_text, turns = runner.run(messages, MM_TOOLS, exec_multiverse)
    passed = score_numeric(float(item["answer"]), final_text)
    return CaseResult("multiverse_math", item["question"][:40], passed, time.time() - t0, turns, tool_calls, item["answer"], final_text, final_text=final_text)


def run_relational(runner: AgentRunner, item: dict) -> CaseResult:
    messages = [
        {"role": "system", "content": "Please answer the user's question by using the tools provided. Do not guess the answer. Keep in mind that entities like users, foods and locations have both a name and an ID, which are not the same."},
        {"role": "user", "content": item["question"]},
    ]
    t0 = time.time()
    _, tool_calls, final_text, turns = runner.run(messages, relational_tools(), exec_relational)
    passed = score_keywords(item["keywords"], final_text)
    return CaseResult("relational_data", item["question"][:40], passed, time.time() - t0, turns, tool_calls, item["answer"], final_text, final_text=final_text)


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    by_task: dict[str, list[CaseResult]] = {}
    for r in results:
        by_task.setdefault(r.task, []).append(r)
    summary = {}
    for task, items in by_task.items():
        passed = sum(1 for i in items if i.passed)
        summary[task] = {
            "passed": passed,
            "total": len(items),
            "pass_rate": round(passed / len(items), 3) if items else 0,
            "avg_latency_s": round(sum(i.latency_s for i in items) / len(items), 2),
            "avg_turns": round(sum(i.turns for i in items) / len(items), 2),
        }
    total_passed = sum(1 for r in results if r.passed)
    summary["overall"] = {
        "passed": total_passed,
        "total": len(results),
        "pass_rate": round(total_passed / len(results), 3) if results else 0,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=ENDPOINT_DEFAULT)
    parser.add_argument("--model", default="local")
    parser.add_argument("--output", default="")
    parser.add_argument("--quick", action="store_true", help="Run a short subset")
    args = parser.parse_args()

    runner = AgentRunner(args.endpoint, args.model)
    results: list[CaseResult] = []

    strings = STRINGS_TO_TYPE[:6] if args.quick else STRINGS_TO_TYPE
    mm_set = MM_DATASET[:5] if args.quick else MM_DATASET
    rel_set = RELATIONAL_QUESTIONS[:3] if args.quick else RELATIONAL_QUESTIONS

    print("=" * 72)
    print("BRUTAL LANGCHAIN TOOL-USE EVAL")
    print(f"Endpoint: {args.endpoint}")
    print(f"Model: {args.model}")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 72)

    for word in strings:
        r = safe_run("typewriter_1", word, lambda w=word: run_typewriter_1(runner, w))
        results.append(r)
        mark = "PASS" if r.passed else "FAIL"
        print(f"[typewriter_1] {word:15s} {mark:4s} turns={r.turns:2d} tools={len(r.tool_calls):3d} actual={r.actual!r} latency={r.latency_s:.1f}s" + (f" err={r.detail}" if r.detail else ""))

    for word in strings:
        r = safe_run("typewriter_26", word, lambda w=word: run_typewriter_26(runner, w))
        results.append(r)
        mark = "PASS" if r.passed else "FAIL"
        print(f"[typewriter_26] {word:15s} {mark:4s} turns={r.turns:2d} tools={len(r.tool_calls):3d} actual={r.actual!r} latency={r.latency_s:.1f}s" + (f" err={r.detail}" if r.detail else ""))

    for item in mm_set:
        r = safe_run("multiverse_math", item["question"][:40], lambda it=item: run_multiverse(runner, it))
        results.append(r)
        mark = "PASS" if r.passed else "FAIL"
        got = (r.actual or "")[:60]
        print(f"[multiverse] {r.case_id:40s} {mark:4s} expected={r.expected} got={got!r} tools={len(r.tool_calls)}" + (f" err={r.detail}" if r.detail else ""))

    for item in rel_set:
        r = safe_run("relational_data", item["question"][:40], lambda it=item: run_relational(runner, it))
        results.append(r)
        mark = "PASS" if r.passed else "FAIL"
        ans = (r.actual or "")[:80]
        print(f"[relational] {r.case_id:40s} {mark:4s} tools={len(r.tool_calls)} answer={ans!r}" + (f" err={r.detail}" if r.detail else ""))

    summary = summarize(results)
    print("\n" + "=" * 72)
    print("SUMMARY")
    for task, stats in summary.items():
        if task == "overall":
            continue
        print(f"  {task:16s}: {stats['passed']}/{stats['total']} ({stats['pass_rate']*100:.1f}%) avg_turns={stats['avg_turns']} avg_lat={stats['avg_latency_s']}s")
    ov = summary["overall"]
    print(f"  {'OVERALL':16s}: {ov['passed']}/{ov['total']} ({ov['pass_rate']*100:.1f}%)")
    print("=" * 72)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": args.endpoint,
        "model": args.model,
        "summary": summary,
        "results": [r.__dict__ for r in results],
    }
    out = Path(args.output) if args.output else Path(f"/home/dino/logs/model-tests/ornith-35b-langchain-brutal-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()