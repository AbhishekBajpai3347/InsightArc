# Insight-Arc Architecture Walkthrough

Welcome to the complete, interactive learning package for understanding the internal design and execution of the Insight-Arc application.

## Directory Structure
- **`interactive/index.html`**: A self-contained, locally viewable HTML/JavaScript execution simulator. Open this file in your browser to step through realistic scenarios (Simple Query, Multi-step Derived Result, Independent Operations, Dataset Modification, Errors, Provider Fallback).
- **`presentation/presentation.md`**: A comprehensive, progressive Markdown presentation covering the architecture from end to end.
- **`reference/function-reference.md`**: A detailed, function-by-function reference of the core execution path.
- **`reference/call-graph.md`**: Mermaid-based diagrams showing call graphs, provider fallback, and end-to-end request lifecycles.
- **`reference/state-lifecycle.md`**: Detailed explanation of `current_df`, `last_result`, and how data flows through the system.
- **`reference/adding-new-tools.md`**: Developer guide on how to add new tools to the architecture.

## How to use the Interactive Simulator
1. Open `interactive/index.html` in any modern web browser (no local web server required).
2. Select a scenario from the sidebar (e.g., "Scenario B: Multi-step derived result").
3. Use the "Next Step" and "Previous Step" buttons to step through the exact code path the application takes to execute the query.

## Important Note
This documentation is derived entirely from the actual, current source code. It traces real functions, real variable assignments, and the actual split between the local `web_app` / `intelligence` layer and the `hosted_server` LLM backend. No code modifications were made to the application during the generation of these documents.
