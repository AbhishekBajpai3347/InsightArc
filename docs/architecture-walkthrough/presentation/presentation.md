# Insight-Arc Architecture

## 1. What Insight-Arc Does
Insight-Arc is a local, privacy-first conversational data analysis tool. It processes large local datasets using Python and Pandas on your machine, while outsourcing only the *reasoning* (tool selection and logic generation) to a hosted LLM server.

## 2. Local App vs Hosted Backend
- **Local (`web_app`, `intelligence`)**: Holds your CSVs. Executes the Python code. Never sends actual dataset values over the internet unless explicitly sampled in a tool observation.
- **Hosted (`hosted_server`)**: Holds the LLM API keys. Manages the system prompt. Formats the ReAct prompt.

## 3. The `current_df` vs `last_result` Paradigm
To handle huge files (e.g., 8 million rows), the system maintains two parallel states:
1. `current_df`: The massive active dataset.
2. `last_result`: A cached, small DataFrame resulting from an intermediate step (like a groupby).

## 4. Plotting Guardrails
If the LLM tries to execute `plot_scatter` on 8 million rows, the system will freeze.
- `executor.py` enforces a `max_input_rows` limit before the tool even runs.
- If breached, it immediately throws a `ValueError` observation back to the LLM, prompting it to filter or group the data first.

## 5. Provider Fallback
In `hosted_server/core.py`, requests are routed primarily to DeepInfra. If a transient error occurs (timeout, rate limit), the loop gracefully catches the error and instantly resubmits the exact same payload to Groq, isolating the user from infrastructure instability.
