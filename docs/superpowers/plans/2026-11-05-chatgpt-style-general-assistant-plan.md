# ChatGPT-Style General Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let BevIQ handle normal ChatGPT-style conversation, jokes, general questions, follow-ups, and English/Roman Hinglish language matching while preserving verified beverage-data routing.

**Architecture:** Keep the existing `RAGOrchestrator` as the single routing boundary. Non-catalog messages go to Ollama with recent conversation context and a language instruction; catalog/document messages retain their existing verified retrieval paths. Local deterministic fallbacks remain available when Ollama is unavailable.

**Tech Stack:** Python, Flask, Ollama HTTP API, pytest.

**Spec:** `docs/superpowers/specs/2026-11-05-chatgpt-style-general-assistant-design.md`

## Global Constraints

- Use the existing local Ollama architecture; do not add a paid hosted ChatGPT/OpenAI dependency.
- Do not invent beverage-data answers without verified database or document context.
- Preserve dashboard, upload, export, and comparison behavior.
- Match the latest user message: English, Roman Hinglish, or Devanagari Hindi.

## Review Focus

- Casual English with catalog-like words such as “day” or “India” must not trigger catalog retrieval — covered in Task 1.
- Roman Hinglish follow-ups must stay Roman Hinglish even when conversation history is English — covered in Task 1.
- Joke requests must receive a conversational response without SQL/vector access — covered in Task 1.
- General questions with Ollama unavailable must receive a useful fallback rather than a server error — covered in Task 2.
- Catalog questions must still use verified records and language-aware synthesis — covered in Task 2.

### Task 1: Lock down ChatGPT-style routing behavior

**Files:**
- Modify: `tests/test_chat_routing.py`
- Test: `tests/test_chat_routing.py`

**Interfaces:**
- Consumes: `RAGOrchestrator.route_and_execute()` and its existing Ollama hooks.
- Produces: regression tests that define general-chat routing and language behavior.

- [ ] **Step 1: Write failing tests** for a joke request, a casual English question containing a catalog-like word, a Roman Hinglish follow-up, and preserved conversation context.
- [ ] **Step 2: Run the focused tests** with `pytest tests/test_chat_routing.py -q`; confirm any failure is caused by the missing desired behavior, not a test setup error.
- [ ] **Step 3: Implement only the minimum routing/prompt changes** in `engines/rag_orchestrator.py` required by the failing tests. Keep catalog intent detection separate from general chat.
- [ ] **Step 4: Re-run the focused tests** and confirm they pass.
- [ ] **Step 5: Commit** with `git commit -m "test: define chatgpt-style conversation behavior"` after staging only the task files.

### Task 2: Improve fallback and verified data conversation

**Files:**
- Modify: `engines/rag_orchestrator.py`
- Modify: `tests/test_chat_routing.py`

**Interfaces:**
- Consumes: Task 1’s routing expectations and existing `_language_response_instruction()`.
- Produces: robust local fallback behavior and language-aware data synthesis without changing endpoint contracts.

- [ ] **Step 1: Add failing tests** for Ollama-unavailable general questions and English/Hinglish verified data answers.
- [ ] **Step 2: Run only those tests** and confirm the expected failures.
- [ ] **Step 3: Implement the smallest fallback/prompt changes** in `engines/rag_orchestrator.py`; do not alter database query results or response schema.
- [ ] **Step 4: Run the focused routing tests**, then run the full suite with `pytest -q`.
- [ ] **Step 5: Commit** with `git commit -m "feat: support general chat alongside beverage data"`.

### Task 3: Final verification

**Files:**
- Verify: `app.py`, `engines/rag_orchestrator.py`, `tests/test_chat_routing.py`

- [ ] **Step 1:** Run `git diff --check` and confirm no conflict markers remain.
- [ ] **Step 2:** Run the full test suite with `pytest -q` and record the exact result.
- [ ] **Step 3:** Confirm the Flask app and Ollama processes are reachable locally, without pushing to GitHub.
- [ ] **Step 4:** Review `git status` and report any intentionally untracked files separately.
