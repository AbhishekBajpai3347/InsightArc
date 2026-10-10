const scenarios = [
    {
        "title": "Scenario A: Simple analytical query",
        "description": "What is the average fare?",
        "steps": [
            {
                "purpose": "Receive User Request",
                "file": "intelligence/chatbot.py",
                "functionName": "run_chat",
                "caller": "web_app/engine.py -> query()",
                "nextFunction": "call_hosted_llm",
                "codeExcerpt": "def run_chat(user_message: str, df: pd.DataFrame, ...):\n    turn_messages = [{\"role\": \"user\", \"content\": user_message}]\n    ...",
                "inputArgs": {
                    "user_message": "What is the average fare?"
                },
                "returnValue": null,
                "llmContacted": false,
                "toolAction": null,
                "currentDfMeta": "8.3M rows x 12 columns",
                "currentDfHtml": "<table><tr><th>fare_amount</th><th>...</th></tr><tr><td>7.50</td><td>...</td></tr></table>",
                "lastResultMeta": "None",
                "explanation": "This is the entry point for the ReAct loop. It initializes the turn context, taking the user's message and the active DataFrame."
            },
            {
                "purpose": "Query LLM for Tool Selection",
                "file": "intelligence/chatbot.py",
                "functionName": "call_hosted_llm",
                "caller": "run_chat",
                "nextFunction": "hosted_server/main.py -> step()",
                "codeExcerpt": "assistant_message = call_hosted_llm(dataset_info, memory, turn_messages, tools)",
                "inputArgs": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "What is the average fare?"
                        }
                    ]
                },
                "returnValue": {
                    "tool_calls": [
                        {
                            "name": "calculate_statistic",
                            "arguments": "{\"column\": \"fare_amount\", \"statistic\": \"mean\"}"
                        }
                    ]
                },
                "llmContacted": true,
                "toolAction": "Requested",
                "currentDfMeta": "8.3M rows x 12 columns",
                "lastResultMeta": "None",
                "explanation": "The local app contacts the hosted LLM backend via HTTP. It passes dataset metadata, not the actual rows. The LLM decides it needs the 'calculate_statistic' tool."
            },
            {
                "purpose": "Execute Tool",
                "file": "intelligence/executor.py",
                "functionName": "execute_tool",
                "caller": "run_chat",
                "nextFunction": "analysis/statistics.py -> calculate_statistic",
                "codeExcerpt": "input_df = choose_input(tool, source, df, previous_result)\nvalidated = tool.input_schema.model_validate(args)\nresult = tool.function(input_df, **args)",
                "inputArgs": {
                    "tool_name": "calculate_statistic",
                    "args": {
                        "column": "fare_amount",
                        "statistic": "mean"
                    }
                },
                "returnValue": {
                    "result": 14.25,
                    "modifies_dataset": false,
                    "derived_result": null,
                    "figure_png": null
                },
                "llmContacted": false,
                "toolAction": "Executed",
                "currentDfMeta": "8.3M rows x 12 columns",
                "lastResultMeta": "None",
                "explanation": "The executor safely validates the LLM's arguments using Pydantic, routes 'current_df' (since source='dataset' by default), and calls the actual pandas logic."
            },
            {
                "purpose": "Serialize Observation",
                "file": "intelligence/chatbot.py",
                "functionName": "build_observation",
                "caller": "run_chat",
                "nextFunction": "call_hosted_llm (2nd time)",
                "codeExcerpt": "observation = build_observation(execution[\"result\"], modifies=False)\nturn_messages.append({\"role\": \"tool\", \"content\": observation})",
                "inputArgs": {
                    "result": 14.25,
                    "modifies_dataset": false
                },
                "returnValue": "status: success\n14.25",
                "llmContacted": false,
                "toolAction": "Returned",
                "currentDfMeta": "8.3M rows x 12 columns",
                "lastResultMeta": "None",
                "explanation": "The raw float result is packaged into a compact text string so the LLM can read the tool's output without crashing on large data types."
            },
            {
                "purpose": "LLM Generates Final Answer",
                "file": "hosted_server/core.py",
                "functionName": "run_step",
                "caller": "call_hosted_llm",
                "nextFunction": "Return to User",
                "codeExcerpt": "response = client.chat.completions.create(**request)\nreturn {\"message\": message_to_dict(response.choices[0].message)}",
                "inputArgs": {
                    "messages": [
                        "...",
                        {
                            "role": "tool",
                            "content": "status: success\\n14.25"
                        }
                    ]
                },
                "returnValue": {
                    "content": "The average fare is $14.25."
                },
                "llmContacted": true,
                "toolAction": null,
                "currentDfMeta": "8.3M rows x 12 columns",
                "lastResultMeta": "None",
                "explanation": "The LLM reads the tool output and synthesizes the final user-facing string. It outputs no tool calls, breaking the ReAct loop."
            }
        ]
    },
    {
        "title": "Scenario B: Multi-step derived result",
        "description": "Show me a bar chart of total amount per hour.",
        "steps": [
            {
                "purpose": "LLM Selects Aggregation Tool",
                "file": "intelligence/chatbot.py",
                "functionName": "call_hosted_llm",
                "caller": "run_chat",
                "nextFunction": "executor.py -> execute_tool",
                "codeExcerpt": "assistant_message = call_hosted_llm(...)",
                "inputArgs": {
                    "user_message": "Show me a bar chart of total amount per hour."
                },
                "returnValue": {
                    "tool_calls": [
                        {
                            "name": "groupby_aggregate",
                            "arguments": "{\"group_column\": \"hour\", \"value_column\": \"total_amount\", \"aggregation\": \"sum\", \"source\": \"dataset\"}"
                        }
                    ]
                },
                "llmContacted": true,
                "toolAction": "Requested",
                "currentDfMeta": "8.3M rows x 12 columns",
                "lastResultMeta": "None",
                "explanation": "The LLM correctly realizes it must group the massive dataset FIRST before plotting, to avoid passing 8.3M rows to a charting function."
            },
            {
                "purpose": "Save Derived Result",
                "file": "intelligence/executor.py",
                "functionName": "execute_tool",
                "caller": "run_chat",
                "nextFunction": "build_observation",
                "codeExcerpt": "if not tool.modifies_dataset:\n    if isinstance(result, pd.DataFrame):\n        derived_result = result",
                "inputArgs": {
                    "tool_name": "groupby_aggregate",
                    "source": "dataset"
                },
                "returnValue": {
                    "derived_result": "<DataFrame 24 rows>"
                },
                "llmContacted": false,
                "toolAction": "Executed",
                "currentDfMeta": "8.3M rows x 12 columns",
                "lastResultMeta": "24 rows x 2 columns (hour, total_amount)",
                "explanation": "The executor detects the tool returned a DataFrame. Because it didn't modify the main dataset, it caches this 24-row DataFrame as the `derived_result`."
            },
            {
                "purpose": "LLM Plots Derived Result",
                "file": "intelligence/executor.py",
                "functionName": "choose_input",
                "caller": "execute_tool",
                "nextFunction": "analysis/visualization.py -> plot_bar_chart",
                "codeExcerpt": "if source == \"previous_result\":\n    return previous_result",
                "inputArgs": {
                    "source": "previous_result",
                    "x_column": "hour",
                    "y_column": "total_amount"
                },
                "returnValue": {
                    "figure_png": "base64..."
                },
                "llmContacted": false,
                "toolAction": "Executed",
                "currentDfMeta": "8.3M rows x 12 columns",
                "lastResultMeta": "24 rows x 2 columns",
                "explanation": "The LLM explicitly calls `plot_bar_chart` with `source=\"previous_result\"`. The executor grabs the 24-row `last_result` instead of the 8.3M row `current_df`, ensuring lightning-fast and safe plotting."
            }
        ]
    },
    {
        "title": "Scenario C: Independent operations",
        "description": "Give me the average age and average fare.",
        "steps": [
            {
                "purpose": "First Independent Tool Call",
                "file": "intelligence/executor.py",
                "functionName": "execute_tool",
                "caller": "run_chat",
                "nextFunction": "analysis/statistics.py -> calculate_statistic",
                "codeExcerpt": "input_df = choose_input(tool, source, df, previous_result)",
                "inputArgs": {
                    "tool_name": "calculate_statistic",
                    "args": {
                        "column": "age",
                        "statistic": "mean",
                        "source": "dataset"
                    }
                },
                "returnValue": 35.2,
                "llmContacted": false,
                "toolAction": "Executed",
                "explanation": "The LLM executes the first calculation against the full dataset by defaulting to source='dataset'."
            },
            {
                "purpose": "Second Independent Tool Call",
                "file": "intelligence/executor.py",
                "functionName": "execute_tool",
                "caller": "run_chat",
                "nextFunction": "analysis/statistics.py -> calculate_statistic",
                "codeExcerpt": "input_df = choose_input(tool, source, df, previous_result)",
                "inputArgs": {
                    "tool_name": "calculate_statistic",
                    "args": {
                        "column": "fare",
                        "statistic": "mean",
                        "source": "dataset"
                    }
                },
                "returnValue": 14.5,
                "llmContacted": false,
                "toolAction": "Executed",
                "explanation": "Because the LLM issues a second call with source='dataset', it safely evaluates the second column independently. It does not accidentally chain off the first result."
            }
        ]
    },
    {
        "title": "Scenario D: Dataset modification",
        "description": "Delete the column named passenger_id.",
        "steps": [
            {
                "purpose": "Modify Dataset",
                "file": "data/modify.py",
                "functionName": "delete_column",
                "caller": "executor.py -> execute_tool",
                "nextFunction": "chatbot.py -> run_chat",
                "codeExcerpt": "def delete_column(df, column):\n    return df.drop(columns=[column])",
                "inputArgs": {
                    "column": "passenger_id"
                },
                "returnValue": "<DataFrame 8.3M rows x 11 columns>",
                "llmContacted": false,
                "toolAction": "Executed",
                "currentDfMeta": "8.3M rows x 11 columns",
                "lastResultMeta": "None",
                "explanation": "The Python function drops the column and returns a brand new DataFrame. The executor flags `modifies_dataset=True`."
            },
            {
                "purpose": "Invalidate Stale State",
                "file": "intelligence/chatbot.py",
                "functionName": "run_chat",
                "caller": "N/A",
                "nextFunction": "build_observation",
                "codeExcerpt": "if modifies:\n    last_result = None  # results computed from old dataset are stale",
                "inputArgs": {
                    "modifies": true
                },
                "returnValue": null,
                "llmContacted": false,
                "toolAction": "None",
                "currentDfMeta": "8.3M rows x 11 columns",
                "lastResultMeta": "None (Cleared)",
                "explanation": "Crucial step: because the active dataset changed, any previously cached `last_result` is now mathematically invalid. The chatbot instantly wipes `last_result`."
            }
        ]
    },
    {
        "title": "Scenario E: Invalid request or tool error",
        "description": "Calculate average of non_existent_column",
        "steps": [
            {
                "purpose": "Tool Fails Validation or Execution",
                "file": "intelligence/executor.py",
                "functionName": "execute_tool",
                "caller": "run_chat",
                "nextFunction": "Exception Handler",
                "codeExcerpt": "except ValidationError as e:\n    raise ValueError(...) from e",
                "inputArgs": {
                    "args": {
                        "column": "non_existent"
                    }
                },
                "returnValue": "ValueError('Column not found')",
                "llmContacted": false,
                "toolAction": "Executed",
                "isError": true,
                "explanation": "The tool crashes either because of Pydantic schema validation or an explicit KeyError in Pandas."
            },
            {
                "purpose": "Error Observation to LLM",
                "file": "intelligence/chatbot.py",
                "functionName": "run_chat",
                "caller": "executor.py",
                "nextFunction": "call_hosted_llm",
                "codeExcerpt": "except Exception as e:\n    observation = error_observation(str(e))",
                "inputArgs": {
                    "error": "Column not found"
                },
                "returnValue": "status: error\\nerror: Column not found",
                "llmContacted": false,
                "toolAction": "Returned",
                "isError": true,
                "explanation": "Instead of crashing the backend, the exception is caught and serialized into a safe text observation. This allows the LLM to read its mistake and correct its next tool call."
            }
        ]
    },
    {
        "title": "Scenario F: Provider failure and fallback",
        "description": "DeepInfra times out; fallback to Groq.",
        "steps": [
            {
                "purpose": "Primary Provider Fails",
                "file": "hosted_server/core.py",
                "functionName": "run_step",
                "caller": "main.py",
                "nextFunction": "Fallback Loop",
                "codeExcerpt": "try:\n    response = client.chat.completions.create(**request)\nexcept Exception as error:\n    if i < len(providers) - 1:\n        continue",
                "inputArgs": {
                    "client": "DeepInfra (OpenAI)",
                    "model": "GLM-5.3-Flash"
                },
                "returnValue": "TimeoutError",
                "llmContacted": true,
                "toolAction": null,
                "isError": true,
                "explanation": "The primary provider (DeepInfra) is called but times out or returns a 502/429 error. The exception is caught, and because another provider exists in the list, the loop continues."
            },
            {
                "purpose": "Fallback Provider Succeeds",
                "file": "hosted_server/core.py",
                "functionName": "run_step",
                "caller": "main.py",
                "nextFunction": "Return message",
                "codeExcerpt": "response = client.chat.completions.create(**request)\nreturn {\"message\": message_to_dict(...)}",
                "inputArgs": {
                    "client": "Groq",
                    "model": "openai/gpt-oss-20b"
                },
                "returnValue": {
                    "content": "Here is the result..."
                },
                "llmContacted": true,
                "toolAction": null,
                "explanation": "The `core.py` loop seamlessly retries the identical payload against the Groq client, hiding the transient failure from the local application."
            }
        ]
    }
];
