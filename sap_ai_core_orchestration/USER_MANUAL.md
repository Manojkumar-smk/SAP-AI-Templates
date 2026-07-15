# SAP AI Core — Orchestration Service — User Manual

Mini templates for the **Orchestration Service** in SAP AI Core — the managed
pipeline layer that sits in front of an LLM and can chain templating, content
filtering, data masking, document grounding, and structured output into a
single declarative config.

> **SDK note:** This uses `sap-ai-sdk-gen` (the successor to the deprecated
> `generative-ai-hub-sdk`), Python module path `gen_ai_hub.orchestration.*`.
> Class/parameter names occasionally change between SDK minor versions —
> if an import fails, check the installed version's docs at
> [help.sap.com/doc/generative-ai-hub-sdk](https://help.sap.com/doc/generative-ai-hub-sdk/CLOUD/en-US/index.html).

---

## Folder Structure

```
sap_ai_core_orchestration/
├── orchestration_setup.py           ← Auth + OrchestrationService client
├── templating_module.py             ← Template, placeholders, few-shot
├── llm_module.py                    ← Model choice + generation params
├── content_filtering_module.py      ← Input/output safety filters
├── data_masking_module.py           ← PII anonymization/pseudonymization
├── document_grounding_module.py     ← Managed RAG (retrieval + injection)
├── structured_output_module.py      ← JSON-schema constrained output
├── conversation_history_module.py   ← Multi-turn memory (stateless API)
├── orchestration_pipeline.py        ← ALL modules combined in one config
├── orchestration_agent.py           ← Runnable CLI chatbot (the "project")
├── .env.example                     ← Template for your .env file
├── requirements.txt                 ← All pip dependencies
└── USER_MANUAL.md                   ← This file
```

---

## How the Pieces Fit Together

```
                     orchestration_setup.py
                     (auth + OrchestrationService client)
                              │
      ┌───────────────┬───────┴────────┬─────────────────┐
      ▼               ▼                ▼                  ▼
templating_module  llm_module   content_filtering   data_masking
      │               │            _module            _module
      └───────┬───────┴────────┬──────┘                  │
              ▼                ▼                          │
      document_grounding   structured_output               │
          _module              _module                     │
              └────────────────┬────────────────────────────┘
                                ▼
                    orchestration_pipeline.py
                (wires ALL modules into one OrchestrationConfig)
                                │
                                ▼
                    orchestration_agent.py
              (stateful class + CLI — conversation_history_module
               plugged in for multi-turn memory)
```

Each module file is a **standalone, runnable concept lesson** — read it,
run it, understand that one piece. `orchestration_pipeline.py` and
`orchestration_agent.py` are where they all get connected into something
you'd actually ship.

---

## Quick Decision Guide

| I want to… | Use this file |
|------------|--------------|
| Understand auth / connect to the orchestration deployment | `orchestration_setup.py` |
| Build reusable prompts with placeholders / few-shot examples | `templating_module.py` |
| Configure which model + generation params to use | `llm_module.py` |
| Block unsafe input or output | `content_filtering_module.py` |
| Strip/mask PII before it reaches the LLM | `data_masking_module.py` |
| Do RAG without hand-building retrieval | `document_grounding_module.py` |
| Force JSON output for downstream code to consume | `structured_output_module.py` |
| Build multi-turn chat memory | `conversation_history_module.py` |
| See every module combined in one config | `orchestration_pipeline.py` |
| Run a working chatbot right now | `orchestration_agent.py` |

---

## Setup (One-Time)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Confirm you have an orchestration deployment
SAP AI Core creates one automatically in your default resource group
during onboarding. Check: **AI Launchpad → ML Operations → Deployments**,
filter by scenario `orchestration`, status `RUNNING`.

### 3. Create your `.env` file
```bash
cp .env.example .env
```
Fill in your AI Core service key values (from BTP Cockpit → your AI Core
instance → Service Keys):
```
AICORE_AUTH_URL=...
AICORE_CLIENT_ID=...
AICORE_CLIENT_SECRET=...
AICORE_BASE_URL=...
AICORE_RESOURCE_GROUP=default
```
`ORCHESTRATION_DEPLOYMENT_URL` is optional — leave blank to let the SDK
auto-discover your running orchestration deployment.

---

## File-by-File Guide

### `orchestration_setup.py` — Client Setup
**What it does:** Builds the `OrchestrationService` client every other file
imports. Explains orchestration vs. a plain LLM proxy conceptually.
```bash
python orchestration_setup.py
```

### `templating_module.py` — Templating
**What it does:** `Template` + `SystemMessage`/`UserMessage`/`AssistantMessage`
+ `{{?placeholder}}` substitution + few-shot example patterns.
```python
from templating_module import build_template, build_few_shot_template
template = build_template(system_prompt="You are concise.")
```

### `llm_module.py` — Model Selection
**What it does:** Wraps model name/version/params behind one harmonized
interface — swap providers by changing a string, not rewriting code.
```python
from llm_module import build_llm
llm = build_llm(model="gpt-4o", temperature=0.3, max_tokens=800)
```

### `content_filtering_module.py` — Safety Filtering
**What it does:** `AzureContentFilter` severity thresholds applied to
input and/or output.
```python
from content_filtering_module import build_filtering, STRICT_FILTER
filtering = build_filtering(input_filter=STRICT_FILTER, output_filter=STRICT_FILTER)
```

### `data_masking_module.py` — PII Masking
**What it does:** SAP Data Privacy Integration — anonymize (one-way) or
pseudonymize (auto-restored in the final response) PII before the LLM sees it.
```python
from data_masking_module import build_masking
from gen_ai_hub.orchestration.models.sap_data_privacy_integration import MaskingMethod
masking = build_masking(method=MaskingMethod.PSEUDONYMIZATION)
```

### `document_grounding_module.py` — Managed RAG
**What it does:** Retrieval + context injection handled by SAP AI Core,
via linked input/output placeholders. Compare with the DIY pipeline in
`../hana_rag/rag_pipeline.py`.
```python
from document_grounding_module import build_grounding
grounding = build_grounding(data_repositories=["*"])
```

### `structured_output_module.py` — JSON-Constrained Output
**What it does:** Forces the LLM's response to validate against a JSON
Schema — safe to `json.loads()` directly.
```python
from structured_output_module import build_structured_template, TICKET_SCHEMA
template = build_structured_template(TICKET_SCHEMA)
```

### `conversation_history_module.py` — Multi-Turn Memory
**What it does:** Orchestration is stateless — this file shows the
client-side `ConversationBuffer` pattern needed to fake memory via
`messages_history`.
```python
from conversation_history_module import ConversationBuffer, ask
buffer = ConversationBuffer(max_turns=10)
```

### `orchestration_pipeline.py` — Full Pipeline
**What it does:** Combines masking + filtering + templating + grounding +
LLM into one `OrchestrationConfig`, with graceful error handling for
filter blocks.
```bash
python orchestration_pipeline.py
```

### `orchestration_agent.py` — Runnable Project
**What it does:** A stateful `OrchestrationAgent` class + interactive CLI
chatbot with three modes (`general` / `grounded` / `strict`). This is the
"simple project" tying every module together.
```bash
python orchestration_agent.py
```
```
You: My name is Priya, my email is priya@example.com
Bot [general]: Nice to meet you, Priya!

You: /mode strict
Bot: Switched to 'strict' mode (conversation reset).
```

---

## Common Errors

| Error | Fix |
|-------|-----|
| No orchestration deployment found | Check AI Launchpad → Deployments → scenario `orchestration` is `RUNNING`, or set `ORCHESTRATION_DEPLOYMENT_URL` explicitly |
| `AICORE_CLIENT_ID` / auth errors | Re-check your service key values in `.env` against BTP Cockpit |
| Content filter blocks a request unexpectedly | Lower filter strictness (use `RELAXED_FILTER` instead of `STRICT_FILTER`) or check which category (hate/violence/self_harm/sexual) triggered it |
| Grounding returns empty context | No documents ingested into the data repository yet, or `data_repositories` filter doesn't match |
| `json.loads()` fails on structured output | Confirm `strict: true` is set on the response format and the schema has no ambiguous types |
| Import error on a `gen_ai_hub.orchestration.*` submodule | Your installed `sap-ai-sdk-gen` version may have renamed a class — check the changelog / current API docs |

---

## How This Relates to the Other Mini Templates

`hana_ai_query/`, `hana_rag/`, `sap_chatbot/` etc. call the LLM **directly**
through the Gen AI Hub proxy (`gen_ai_hub.proxy.langchain.openai.ChatOpenAI`)
and you write the masking/filtering/RAG glue code yourself in Python.

This folder uses the **Orchestration Service** instead — the same
capabilities (RAG, safety, PII protection), but configured declaratively
and executed server-side by SAP AI Core. Learn both: proxy-direct for
simple single-model calls, orchestration for anything that needs a
governed, multi-step, auditable pipeline.
