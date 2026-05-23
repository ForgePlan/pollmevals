# 09 — Stack Adapter Guide

## Goal

A stack adapter describes how a full LLM stack is executed reproducibly.

A stack is not just a model. It can include:

- base model;
- agent CLI;
- system prompt;
- tools;
- skills;
- file memory;
- vector memory;
- subagents;
- validator loop;
- domain framework.

## Required structure

```text
stacks/{stack_slug}/
  stack.yaml
  adapter.sh or adapter.py
  README.md
  reproduce.md
```

## Required fields

```yaml
stack_adapter_version: "1.0"
slug: claude-code-basic
name: Claude Code Basic
base_model_slug: claude-sonnet
agent_cli: claude-code
agent_cli_version: pinned-version
execution_mode: repository_patch
layers:
  L0_bare_llm: false
  L1_system_prompt: true
  L2_tools: true
  L3_skills: false
  L4_file_memory: false
  L5_vector_memory: null
  L6_subagents: false
  L7_validator: false
  L8_framework: null
limits:
  max_wall_clock_seconds: 600
  max_tool_calls: 50
  max_tokens_input: 50000
  max_tokens_output: 10000
sandbox:
  network: false
  writable_paths:
    - /workspace
output_contract:
  produces:
    - final_answer
    - patch
    - tool_trace
```

## Fairness policy

All stack evaluations must specify:

- token budget;
- wall-clock budget;
- whether tests can be run;
- whether retry is allowed;
- whether network access is allowed;
- whether repo-wide reading is allowed;
- how tool-call cost is counted;
- how failed partial outputs are scored.

## Stack comparison rules

1. Compare stacks only inside the same task version.
2. Publish cost overhead and quality lift together.
3. Publish latency overhead for agentic stacks.
4. Do not compare interactive agents against one-shot LLMs without explaining different execution mode.
5. If a stack uses a framework developed by the operator, disclose conflict of interest.
