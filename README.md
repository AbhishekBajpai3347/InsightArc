# Insight-Arc: Conversational Data Analysis Agent

Insight-Arc is an agentic, AI-powered conversational tool for data analysis. It allows users to upload datasets (CSV, Excel, etc.) and interact with them using natural language. The system autonomously writes and executes data operations, generates charts, calculates statistics, and modifies datasets on the fly.

## 🏗️ High-Level Architecture

The project is split into a **Local Client** and a **Hosted Server**:
1. **Local Client (`web_app`, `data`, `analysis`, `intelligence`)**: Runs on the user's machine. It holds the actual data (`pandas.DataFrame`) in RAM, executes all Python data operations locally, and serves the UI. **Raw data never leaves the local machine.**
2. **Hosted Server (`hosted_server`)**: A stateless proxy that holds the LLM API keys (Groq) and the system prompt. It receives structural metadata (column names, types, row counts) and chat history from the local client, passes them to the LLM, and returns the LLM's planned tool calls.

---

## 📂 Project Structure & Key Files

### 1. `web_app/` (The Application Layer)
Manages the local web server, UI, and application state.
* **`engine.py`**: The central nervous system of the local app. It maintains the in-memory state (`_df`, `_filename`, `_memory`) wrapped in a thread `_lock`.
  * *Important Function*: `load()` - Handles file uploads, saves them temporarily, runs them through the data loader/cleaner, and updates the global state.
  * *Important Function*: `query()` - Entry point for user messages, hands them off to the chatbot, and returns the UI-formatted reply via `build_reply()`.
* **`routes.py`**: FastAPI endpoints (`/api/chat`, `/api/dataset/upload`).
* **`static/`**: Contains Vanilla JS frontend files (`app.js`, `api.js`, `messages.js`).

### 2. `intelligence/` (The Agentic Brain)
Handles the LLM ReAct (Reasoning and Acting) loop and tool orchestration.
* **`chatbot.py`**: The core ReAct loop.
  * *Important Function*: `run_chat()` - Iterates up to `MAX_ITERATIONS`. In each loop, it calls the hosted LLM, checks if tool calls are requested, executes them, updates the observation, and loops until the LLM returns a final text answer.
  * *Important Function*: `build_observation()` - Formats the results of a tool execution (e.g., slicing a large dataframe to `MAX_ROWS_FOR_LLM` rows) so the LLM gets context without being overwhelmed by tokens.
* **`executor.py`**:
  * *Important Function*: `execute_tool()` - Safely looks up the requested tool from the registry, validates its Pydantic schema, runs it against the current DataFrame, and captures any generated matplotlib figures as base64 images.
* **`tools.py`**: Contains the actual Python implementations of the 25+ tools available to the LLM (e.g., `filter_rows`, `groupby_aggregate`).
* **`tool_definitions.py` / `schemas.py`**: Maps Python functions to JSON schemas that the LLM understands using Pydantic.

### 3. `data/` (The Data Pipeline)
Handles loading, cleaning, and mutating data.
* **`loader.py`**: Maps file extensions (`.csv`, `.xlsx`, `.json`) to their respective pandas read functions.
* **`cleaner.py`**: 
  * *Important Function*: `clean_dataset()` - A composition pipeline that automatically deduplicates rows/columns, standardizes text/column names, drops highly null columns, and imputes missing values (median for numeric, mode for categorical).
* **`modify.py`**: Functions that permanently alter the dataset structure (drop columns, rename, add columns).
* **`validator.py`**: Generates a dataset quality score based on nulls, duplicates, and mixed datatypes.
* **`encoder.py`**: Uses `scikit-learn` for One-Hot and Ordinal encoding.

### 4. `analysis/` (Math & Visuals)
* **`eda.py`**: Multi-pass Exploratory Data Analysis (skewness, kurtosis, distributions, null percentages).
* **`statistics.py`**: Pure numeric aggregations (mean, median, standard deviation).
* **`visualization.py`**: Wraps `matplotlib` and `seaborn`.
  * *Important Mechanism*: Plots are created locally. `_finish_plot()` captures the plot into a BytesIO buffer, encodes it to base64, and safely closes the plot (`plt.close()`) to prevent memory leaks and thread collisions.

### 5. `hosted_server/` (The LLM Proxy)
* **`core.py`**:
  * *Important Function*: `run_step()` - Assembles the System Prompt, Dataset Block (metadata only), Memory Block, and User messages into a single payload for the Groq API. Handles Rate Limits (HTTP 429) gracefully.
* **`prompt.py`**: Contains the highly optimized `SYSTEM_PROMPT` dictating the agent's behavior, tool usage, and constraints.

---

## 🔄 Complete Project Flow Implementation

Here is the step-by-step lifecycle of how Insight-Arc handles a user request:

### Phase 1: Initialization
1. User opens the browser and uploads a dataset (e.g., `sales.csv`).
2. The UI sends a `POST` to `/api/dataset/upload`.
3. `web_app/engine.py:load()` receives the file, saves it to a temp directory, and passes the path to `data/loader.py`.
4. `loader.py` reads it into a pandas DataFrame.
5. The DataFrame is piped through `data/cleaner.py:clean_dataset()`, which scrubs the data.
6. The cleaned DataFrame is saved into local RAM (`_df` variable in `engine.py`), and metadata (column names, dtypes) is returned to the UI sidebar.

### Phase 2: Conversational Loop
1. User types a prompt: *"Show me a bar chart of sales by region."*
2. UI sends a `POST` to `/api/chat`.
3. `engine.py:query()` locks the state and calls `intelligence/chatbot.py:run_chat()`.
4. **ReAct Loop Begins (Iteration 1):**
   * `run_chat()` calls the hosted server via `requests.post()`.
   * The payload contains: User prompt, dataset metadata (not the raw data), and available JSON tool schemas.
   * Hosted Server forwards this to Groq LLM.
   * LLM decides it needs to use a tool and responds with a tool call: `plot_bar_chart(x="region", y="sales")`.
5. **Tool Execution:**
   * `chatbot.py` intercepts the tool call and passes it to `intelligence/executor.py:execute_tool()`.
   * `executor.py` validates arguments and calls the actual function in `analysis/visualization.py`.
   * The chart is drawn, encoded to base64, and returned as a dictionary.
6. **ReAct Loop Continues (Iteration 2):**
   * `chatbot.py` formats the tool result into an "Observation" (e.g., `{"status": "success", "result": "Chart created..."}`).
   * It sends the history + observation back to the Hosted Server -> LLM.
   * The LLM sees the tool succeeded and responds with a final text message: *"Here is the bar chart showing sales by region..."*
7. **Response Building:**
   * The loop breaks. `run_chat()` returns a `ChatResult` object containing the final text, the base64 image (from the last tool run), and the updated DataFrame.
   * `engine.py:build_reply()` constructs a JSON payload containing `{"type": "image", "message": "...", "image": "<base64>"}`.
8. The UI renders the chatbot's text response and displays the image directly in the chat window.

---

## 🔒 Thread Safety & Rate Limiting
* **Locking:** Because pandas and matplotlib are not inherently thread-safe (especially matplotlib's global state), `engine.py` uses `threading.Lock()` to ensure only one user request modifies the dataframe or generates a plot at a time.
* **Rate Limits:** The ReAct loop can make multiple rapid calls to the LLM. `chatbot.py` implements a `REQUEST_DELAY` (e.g., 0.2s) between iterations to prevent tripping Groq's RPM limits, and `core.py` traps HTTP 429 errors to fail gracefully if limits are hit.
