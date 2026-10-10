# State Lifecycle

## `current_df`
* **What is it?** The main, active dataset the user is analyzing.
* **Where does it live?** It originates from the data loader and is stored in `web_app/engine.py` as part of the session state. It is passed into `run_chat` at the beginning of each turn.
* **When is it updated?** It is ONLY mutated when a tool returns `modifies_dataset=True` (e.g., `delete_column`).
* **When is it cleared?** Never. If the user wants to start over, they must upload a new file.

## `last_result`
* **What is it?** A temporary cache storing the `pd.DataFrame` or `pd.Series` returned by the most recently executed, non-modifying analytical tool (like a groupby or filter operation).
* **Where does it live?** Stored as a local variable in `run_chat` and mirrored in the global `_last_result` inside `web_app/engine.py` to persist it across multiple conversational turns.
* **When is it updated?** Whenever a non-modifying tool successfully returns tabular data, `executor.py` captures it as `derived_result`, and `chatbot.py` binds it to `last_result`.
* **When is it cleared?** Instantly, whenever a tool with `modifies_dataset=True` successfully executes. This prevents downstream tools from operating on a stale "snapshot" of a dataset that has since had columns deleted or values altered.

## Tool Result Flow
1. **Tool Output:** Tool returns arbitrary data (DataFrame, float, string, dict).
2. **Executor Capture:** `executor.py` checks if it's tabular and `modifies_dataset=False`. If so, saves it as `derived_result`. If matplotlib plotted a figure, captures it as base64.
3. **Chatbot Cache:** `run_chat` updates `last_result` with `derived_result`.
4. **Observation Building:** `build_observation` serializes the output into a short text representation. The LLM only sees this text, never the raw data or the image.
