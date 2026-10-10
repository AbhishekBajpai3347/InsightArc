"""
ReAct chat loop (local side).

CHANGES FROM THE ORIGINAL
  * The LLM call no longer goes to Groq directly. Each loop step is ONE request to your
    hosted server (POST {HOSTED_SERVER_URL}/v1/step). The Groq key, model, system prompt,
    tool_choice and max_tokens now live on that server.
  * The loop, memory handling, MAX_ITERATIONS and tool execution are unchanged.
  * What the LLM sees after a tool call changed (see build_observation).
  * run_chat now returns a ChatResult instead of (answer, df, memory).
"""

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

from intelligence.tool_definitions import get_llm_tools
from intelligence.executor import execute_tool

if getattr(sys, "frozen", False):
    # Path where the .exe is physically located
    application_path = os.path.dirname(sys.executable)
else:
    # Path when running normally as a .py script
    application_path = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

env_path = os.path.join(application_path, ".env")


load_dotenv(env_path)

HOSTED_SERVER_URL = (os.getenv("HOSTED_SERVER_URL") or "").rstrip("/")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "15"))
REQUEST_DELAY = float(os.getenv("GROQ_REQUEST_DELAY", "0.2"))

REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))  # per call to the hosted server; no retries
MAX_OBSERVATION_CHARS = int(os.getenv("MAX_OBSERVATION_CHARS", "2000"))  # size budget of one tool result shown to the LLM
MEMORY_ENTRY_CHARS = int(os.getenv("MEMORY_ENTRY_CHARS", "600"))        # size budget of one tool entry kept in memory
MEMORY_LIMIT = int(os.getenv("MEMORY_LIMIT", "5"))                  # compact history turns kept in memory

OFFLINE_MESSAGE = "Cannot reach the assistant service. Check your internet connection and try again."
GENERIC_SERVICE_ERROR = "The assistant service could not complete the request. Please try again."


@dataclass
class ChatResult:
    """Everything the caller needs. It deliberately contains no HTTP/JSON/UI details."""

    answer: str                       # the LLM's final text (or an error message)
    dataframe: pd.DataFrame           # the current dataset after this turn
    memory: list[str]                 # analysis memory to pass to the next call
    status: str = "ok"                # "ok" | "partial" | "error"
    last_tool: dict | None = None     # the LAST tool call of the turn, only if it succeeded:
                                      #   {"name", "modifies_dataset", "result", "figure_png"}
    dataset_changed: bool = False     # a modifying tool succeeded during this turn
    last_result: pd.DataFrame | None = None  # latest derived table (pass it to the next call)
    last_chart: dict | None = None    # the last chart drawn this turn (same shape as last_tool),
                                      # so a chart is not lost when another tool runs after it

    # status "partial": the last tool call failed although an earlier one succeeded.
    # status "error"  : there is no usable answer (service unreachable, step limit, ...).


class HostedServiceError(Exception):
    """A failure talking to the hosted server. The message is safe to show to the user."""


def call_hosted_llm(dataset_info: dict, memory: list[str], messages: list[dict], tools: list[dict]) -> dict:
    """One LLM step. Returns the assistant message: {"content": ..., "tool_calls": [...] | None}."""
    hosted_url = (os.getenv("HOSTED_SERVER_URL") or HOSTED_SERVER_URL or "").rstrip("/")
    if not hosted_url:
        raise HostedServiceError("The assistant service address is not configured (HOSTED_SERVER_URL).")

    payload = {"dataset": dataset_info, "memory": memory, "messages": messages, "tools": tools}
    try:
        response = requests.post(
            f"{hosted_url}/v1/step", json=payload, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except requests.ConnectionError:  # also covers "could not connect in time"
        raise HostedServiceError(OFFLINE_MESSAGE) from None
    except requests.Timeout:
        raise HostedServiceError("The assistant service took too long to respond. Please try again.") from None
    except requests.RequestException:
        raise HostedServiceError(GENERIC_SERVICE_ERROR) from None

    try:
        body = response.json()
    except ValueError:
        raise HostedServiceError(GENERIC_SERVICE_ERROR) from None

    if response.status_code != 200:
        detail = body.get("detail") if isinstance(body, dict) else None
        raise HostedServiceError(detail if isinstance(detail, str) else GENERIC_SERVICE_ERROR)

    message = body.get("message") if isinstance(body, dict) else None
    if not isinstance(message, dict):
        raise HostedServiceError(GENERIC_SERVICE_ERROR)
    return message


def fit_text(text: str, budget: int | None = None) -> str:
    """Return text unchanged if it fits the budget, else cut at a line end and say what was cut."""
    budget = budget or MAX_OBSERVATION_CHARS
    if len(text) <= budget:
        return text
    cut = text[:budget].rsplit("\n", 1)[0]
    return cut + f"\n... truncated: {len(text):,} characters in total, over the size budget"


def table_to_text(table: pd.DataFrame) -> str:
    """
    A table as compact CSV, cut to MAX_OBSERVATION_CHARS.

    A CSV row needs at least 2 characters (a value and a line break), so at most
    MAX_OBSERVATION_CHARS // 2 rows can ever fit: only those are serialized, which keeps
    this cheap even for a table with millions of rows.
    """
    lines = table.head(MAX_OBSERVATION_CHARS // 2).to_csv(index=False, lineterminator="\n").splitlines()
    kept = [lines[0]]  # header
    size = len(lines[0])
    for line in lines[1:]:
        if size + 1 + len(line) > MAX_OBSERVATION_CHARS:
            break
        kept.append(line)
        size += 1 + len(line)

    shown = len(kept) - 1
    if shown < len(table):
        kept.append(f"... showing the first {shown:,} of {len(table):,} rows (the rest is over the size budget)")
    return "\n".join(kept)


def build_observation(result: Any, modifies_dataset: bool, chart: str | None = None, saved_as_previous_result: bool = False) -> str:
    """
    What the LLM is told about a SUCCESSFUL tool call: always compact text, never empty.

      * chart            -> one line describing the chart (the picture itself never goes to the LLM)
      * modifying tool   -> new row count and column names ONLY (the result is the whole dataset)
      * DataFrame/Series -> shape + compact CSV (cut to MAX_OBSERVATION_CHARS)
      * anything else    -> the value as text (CSV text, numbers, ...), cut to MAX_OBSERVATION_CHARS
    """
    if chart is not None:
        return f"status: success\n{chart}"

    if isinstance(result, pd.Series):
        result = result.reset_index()

    if isinstance(result, pd.DataFrame):
        shape = f"{len(result):,} rows x {len(result.columns)} columns"
        if modifies_dataset:
            columns = ",".join(str(c) for c in result.columns)
            return f"status: success\ndataset modified: now {shape}; previous_result cleared\ncolumns: {columns}"
        saved = ", saved as previous_result" if saved_as_previous_result else ""
        return f"status: success\nresult: table, {shape}{saved}\n{table_to_text(result)}"

    if isinstance(result, (dict, list)):
        text = json.dumps(result, default=str, separators=(",", ":"))
    else:
        text = str(result)
    text = fit_text(text)
    return f"status: success\nresult:\n{text}" if "\n" in text else f"status: success\nresult: {text}"


def error_observation(message: str) -> str:
    return f"status: error\nerror: {message}"


def describe_chart(name: str, args: dict, execution: dict) -> str:
    """One line about a chart for the LLM and memory, e.g. what was plotted and from how many rows."""
    shown_args = ", ".join(f"{key}={value}" for key, value in args.items() if key != "source")
    return (
        f"chart created and shown to the user (image not included here): {name}({shown_args}), "
        f"{execution['input_rows']:,} rows plotted from {execution['source']}"
    )


def describe_previous_result(last_result: pd.DataFrame | None) -> str:
    """Short text telling the LLM whether a previous_result exists and what it looks like."""
    if last_result is None:
        return "none"
    columns = ",".join(str(c) for c in last_result.columns)
    return f"{len(last_result):,} rows x {len(last_result.columns)} columns ({columns})"


def run_chat(
    user_message: str,
    df: pd.DataFrame,
    memory: list[str] | None = None,
    show_progress: bool = True,
    last_result: pd.DataFrame | None = None,
) -> ChatResult:
    """
    One user turn of the ReAct loop.

    Two pieces of data state, both plain variables:
        current_df  : the active dataset. Changes ONLY when a modifying tool succeeds.
        last_result : the latest table produced by a non-modifying tool (filter, sort, group,
                      counts, ...). Tools use it only when the LLM passes source="previous_result".
                      Cleared when the dataset is modified, so it is never stale.
    """
    try:
        tools = get_llm_tools()
    except Exception as e:
        return ChatResult(f"Initialization failed: {e}", df, memory or [], status="error", last_result=last_result)

    memory = memory or []
    current_df = df

    # Only messages required for THIS ReAct loop.
    turn_messages = [{"role": "user", "content": user_message}]

    dataset_changed = False
    any_success = False   # did at least one tool call succeed this turn?
    last_tool = None      # the last tool call, if it succeeded (None if it failed)
    last_chart = None     # the last chart drawn this turn, if any

    for step_idx in range(MAX_ITERATIONS):
        if step_idx > 0 and REQUEST_DELAY > 0:
            time.sleep(REQUEST_DELAY)

        dataset_info = {
            "rows": len(current_df),
            "columns": {
                str(c): str(dtype) for c, dtype in current_df.dtypes.items()
            },
            "previous_result": describe_previous_result(last_result),
        }

        # -------------------------
        # LLM request (via the hosted server)
        # -------------------------
        try:
            msg = call_hosted_llm(dataset_info, memory, turn_messages, tools)
        except HostedServiceError as e:
            return ChatResult(
                str(e), current_df, memory, status="error", dataset_changed=dataset_changed,
                last_result=last_result,
            )

        tool_calls = msg.get("tool_calls") or []

        # -------------------------
        # Final answer
        # -------------------------
        if not tool_calls:
            answer = msg.get("content") or ""

            # if not answer.strip():
            #     return ChatResult(
            #         "I could not generate an answer.",
            #         current_df,
            #         memory,
            #         status="error",
            #         dataset_changed=dataset_changed,
            #     )

            # Keep only the useful result in persistent memory.
            memory.append(
                f"User asked: {user_message}\n" f"Assistant answered: {answer}"
            )

            # Last tool failed after an earlier one worked -> the caller shows text only, plus a note.
            status = "partial" if any_success and last_tool is None else "ok"

            return ChatResult(
                answer,
                current_df,
                memory[-MEMORY_LIMIT:],
                status=status,
                last_tool=last_tool,
                dataset_changed=dataset_changed,
                last_result=last_result,
                last_chart=last_chart,
            )

        # -------------------------
        # Tool calls
        # -------------------------

        # This exact assistant message MUST stay in the current
        # ReAct loop, but does NOT need to become long-term memory.
        turn_messages.append(
            {
                "role": "assistant",
                "content": msg.get("content"),
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"].get("arguments"),
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:

            name = tc["function"]["name"]
            args = {}

            try:
                args = json.loads(tc["function"].get("arguments") or "{}")

                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be a JSON object.")

                if show_progress:
                    print(f"\n[Tool] {name}")
                    print(f"[Arguments] {args}")


                print("[Executor] BEFORE execute_tool")

                execution = execute_tool(
                    current_df,
                    name,
                    args,
                    last_result,
                )

                print("[Executor] AFTER execute_tool")

                current_df = execution["dataframe"]
                modifies = execution["modifies_dataset"]
                figure_png = execution.get("figure_png")
                result = execution["result"]

                # Move the derived-result slot forward.
                if modifies:
                    last_result = None  # results computed from the old dataset are stale
                elif execution["derived_result"] is not None:
                    last_result = execution["derived_result"]

                # Never expose chart binary data to the LLM: only a one-line description.
                if figure_png is None and isinstance(result, dict) and "image_base64" in result:
                    figure_png = result.get("image_base64")
                if figure_png is not None:
                    observation = build_observation(result, modifies, chart=describe_chart(name, args, execution))
                else:
                    observation = build_observation(
                        execution["derived_result"] if execution["derived_result"] is not None else result,
                        modifies,
                        saved_as_previous_result=execution["derived_result"] is not None,
                    )

                any_success = True
                dataset_changed = dataset_changed or modifies
                last_tool = {
                    "name": name,
                    "modifies_dataset": modifies,
                    "result": result,
                    "figure_png": figure_png,
                }
                if figure_png is not None:
                    last_chart = last_tool

            except json.JSONDecodeError as e:
                last_tool = None
                observation = error_observation(f"Invalid tool arguments: {e}")

            except Exception as e:
                last_tool = None
                observation = error_observation(str(e))

            if show_progress:
                print("[Observation]", observation)

            # Exact tool response is needed for THIS ReAct loop: the full compact text,
            # for successes AND errors (it is never images and never an empty/null value).
            turn_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": name,
                    "content": observation,
                }
            )

            # Store a compact persistent memory entry (charts are already a one-line description).
            memory.append(f"{name}({args}) → {fit_text(observation, MEMORY_ENTRY_CHARS)}")
            memory = memory[-MEMORY_LIMIT:]

    return ChatResult(
        "I could not complete the request within the allowed number of steps.",
        current_df,
        memory,
        status="error",
        dataset_changed=dataset_changed,
        last_result=last_result,
    )

