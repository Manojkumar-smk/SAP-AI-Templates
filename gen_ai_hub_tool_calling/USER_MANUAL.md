# Tool Calling with SAP Gen AI Hub — User Manual

Mini templates for **direct LLM tool/function calling** through the
SAP Gen AI Hub proxy (`gen_ai_hub.proxy.*`) — as opposed to the
Orchestration Service's tool calling (see
`../sap_ai_core_orchestration/tool_calling_module.py`) or exposing
tools over MCP for external agents (see
`../mcp_server_cloud_foundry/`).

> **Verified against:** `sap-ai-sdk-gen` 6.10.0, installed and
> actually run in a test sandbox — schema generation, error paths,
> and the `bind_tools()` mechanics were confirmed working, not just
> written from documentation.

---

## Folder Structure

```
gen_ai_hub_tool_calling/
├── tool_definitions.py       ← Plain functions + shared TOOL_REGISTRY
├── llm_setup.py               ← LangChain + native client builders
├── tool_calling_langchain.py  ← Single-turn tool calling via bind_tools()
├── tool_calling_native.py     ← Single-turn tool calling via raw OpenAI-style API
├── tool_calling_agent.py      ← Full agentic loop (the "project")
├── .env.example
├── requirements.txt
└── USER_MANUAL.md
```

---

## How the Pieces Fit Together

```
                    tool_definitions.py
              (plain functions — no LLM, no schema)
                    │                    │
        convert_to_openai_tool()  bind_tools() [uses the same
        (used directly in            utility internally]
         tool_calling_native.py)          │
                    │                    │
                    ▼                    ▼
        tool_calling_native.py   tool_calling_langchain.py
        (raw OpenAI-compatible    (LangChain AIMessage.tool_calls,
         tools=[...], json.loads   args pre-parsed to a dict)
         the arguments yourself)
                                          │
                                          ▼
                                tool_calling_agent.py
                        (the loop: bind → invoke → detect
                         tool_calls → execute → ToolMessage →
                         invoke again → ... → final answer)
```

Read `tool_definitions.py` first — both calling styles share it.
Then `tool_calling_langchain.py` OR `tool_calling_native.py`
(they demonstrate the SAME single tool call two different ways —
you don't need both in a real project, pick one style). Then
`tool_calling_agent.py` for the multi-turn loop neither single-call
file implements.

---

## Quick Decision Guide

| I want to... | Use this file |
|------------|--------------|
| See the shared, framework-agnostic tool functions | `tool_definitions.py` |
| Get an LLM handle (either style) | `llm_setup.py` |
| Bind tools the LangChain way (pre-parsed args) | `tool_calling_langchain.py` |
| Bind tools the raw OpenAI-SDK way (manual JSON parse) | `tool_calling_native.py` |
| Run a full multi-step tool-calling conversation | `tool_calling_agent.py` |

---

## Setup (One-Time)

### 1. Install dependencies — the `[all]` extra matters here
```bash
pip install -r requirements.txt
```
`gen_ai_hub.proxy.langchain`'s `__init__.py` eagerly imports its
Amazon and Google integrations even though this folder only uses
OpenAI-backed `ChatOpenAI` — installing the bare package (without
`[all]`) causes a `ModuleNotFoundError` for `botocore` the moment
`llm_setup.py` is imported. This was verified directly, not assumed.

### 2. Create your `.env`
```bash
cp .env.example .env
```
Fill in your AI Core service key values and `LLM_DEPLOYMENT_ID`
(SAP AI Launchpad → ML Operations → Deployments — pick one for
scenario `foundation-models`, status `RUNNING`).

### 3. Run each file
```bash
python tool_calling_langchain.py
python tool_calling_native.py
python tool_calling_agent.py
```

---

## LangChain vs. Native — What Actually Differs

| | `tool_calling_langchain.py` | `tool_calling_native.py` |
|---|---|---|
| Tool args in the response | Pre-parsed Python dict (`call['args']`) | JSON string you `json.loads()` yourself (`call.function.arguments`) |
| Tool call access | `response.tool_calls` (list of dicts) | `response.choices[0].message.tool_calls` (OpenAI SDK objects) |
| Depends on | LangChain | Nothing beyond `openai`-compatible client |
| Best for | Codebases already using LangChain chains/agents | Minimal-dependency scripts, or code ported from raw OpenAI SDK usage |

Both derive their tool JSON Schema from the exact same plain Python
functions via LangChain's `convert_to_openai_tool()` utility — there
is no hand-written schema anywhere in this folder.

---

## Common Errors

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'botocore'` on import | Install `sap-ai-sdk-gen[all]`, not the bare package — see Setup step 1 |
| `EnvironmentError: LLM_DEPLOYMENT_ID not set` | Fill in `.env` from `.env.example`; get the ID from AI Launchpad → Deployments |
| Auth error immediately when building `ChatOpenAI(...)` | This happens at CONSTRUCTION time, not just `.invoke()` — `validate_environment` calls `select_deployment()` which authenticates against AI Core right away; check your `AICORE_*` values |
| Model never calls a tool even when it obviously should | Check the tool's docstring has an `Args:` section — without per-parameter descriptions the model has less signal to decide arguments are extractable from the question |
| `tool_calling_agent.py` hits "Max turns reached" | The model kept requesting tools without converging — inspect the printed conversation for a tool that keeps erroring, or raise `max_turns` if the task genuinely needs more steps |

---

## How This Relates to the Other Mini Templates

`hana_ai_query/`, `sap_chatbot/` etc. use the same Gen AI Hub proxy
for plain text generation — no tools. This folder adds tool/function
calling on top of that same proxy. `sap_ai_core_orchestration/`
shows the SAME capability through the managed Orchestration Service
instead (different message/config classes, same underlying idea).
`mcp_server_cloud_foundry/` shows the inverse direction — exposing
Python functions as tools for an EXTERNAL agent (Joule Studio, an
IDE coding assistant) to discover and call, rather than binding them
to an LLM call your own code makes directly.
