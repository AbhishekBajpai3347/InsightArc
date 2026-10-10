# Function-by-Function Reference

This document maps the core execution path of the Insight-Arc application.

## Core Execution & Orchestration

### `run_chat`
* **File:** `intelligence/chatbot.py`
* **Purpose:** Orchestrates a single turn of the ReAct (Reasoning and Acting) loop, coordinating the LLM and tool execution.
* **Inputs:** `user_message: str`, `df: pd.DataFrame`, `memory: list[str]`, `last_result: pd.DataFrame | None`
* **Returns:** `ChatResult` (dataclass containing final answer, updated DataFrame, and memory).
* **Key Variables:** `current_df`, `last_result`, `turn_messages`.
* **Calls:** `call_hosted_llm`, `execute_tool`, `build_observation`, `describe_chart`.
* **LLM Contact:** Yes (via `call_hosted_llm`).
* **State Change:** Yes. Updates `current_df` if modifying tools succeed, and `last_result` for derived results.
* **Why it's necessary:** Without this, there is no state persistence across a single conversational turn. It is the core controller of the agentic loop.

### `call_hosted_llm`
* **File:** `intelligence/chatbot.py`
* **Purpose:** Acts as the network bridge to the hosted LLM server.
* **Inputs:** `dataset_info: dict`, `memory: list[str]`, `messages: list[dict]`, `tools: list[dict]`
* **Returns:** `dict` (assistant message containing content and tool_calls).
* **Why it's necessary:** Segregates the heavy LLM API logic (and secrets) on a hosted server rather than the client application.

### `run_step`
* **File:** `hosted_server/core.py`
* **Purpose:** Executes a single generation step against the configured LLM providers, with automatic fallback handling.
* **Inputs:** `providers: list` (tuples of client & model), `payload: dict`.
* **Returns:** `dict` containing the synthesized assistant message.
* **Errors:** `StepError(429)` or `StepError(502)` if all providers fail. Safely hides raw stack traces from the client.

## Tool Execution & Safety

### `execute_tool`
* **File:** `intelligence/executor.py`
* **Purpose:** Safely executes requested pandas functions, enforces safety guardrails, and captures matplotlib figures.
* **Inputs:** `df: pd.DataFrame`, `tool_name: str`, `arguments: dict`, `previous_result: pd.DataFrame | None`.
* **Returns:** `dict` with `result`, `dataframe`, `modifies_dataset`, `figure_png`, `derived_result`, `source`.
* **Calls:** `choose_input`, tool function (e.g., `plot_bar_chart`), `_capture_figure_png`.
* **Why it's necessary:** It acts as a safety firewall. If removed, the LLM could run expensive functions (like plotting 8 million rows) causing the local app to freeze.

### `choose_input`
* **File:** `intelligence/executor.py`
* **Purpose:** Resolves whether a tool should operate on `current_df` or `last_result`.
* **Inputs:** `tool: ToolDefinition`, `source: str`, `df`, `previous_result`.
* **Returns:** The correct `pd.DataFrame`.
* **Errors:** Raises `ValueError` if `source="previous_result"` but no previous result exists, forcing the LLM to learn and recover.

## Observation & Formatting

### `build_observation`
* **File:** `intelligence/chatbot.py`
* **Purpose:** Serializes a Python object or DataFrame into a highly compact textual CSV string for the LLM prompt.
* **Inputs:** `result: Any`, `modifies_dataset: bool`, `chart: str | None`.
* **Returns:** `str` (the serialized observation).
* **Why it's necessary:** Without this, dumping an 8.3M row DataFrame JSON into the LLM context would instantly breach context limits or result in blind `null` responses.
