# General and Project Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native implementation.

**Goal:** One offline CPU chat for general questions and grounded project explanations while preserving database and upload answers.
**Architecture:** A small project knowledge module matches app-specific explanation questions and provides allowlisted guide/config context to the existing local model. Existing general, database, document and image routes retain their responsibilities.
**Tech Stack:** Python, Flask, existing Ollama/SQLite, pathlib/re; no new dependency.
**Spec:** docs/superpowers/specs/2026-11-11-general-project-chat-design.md

## Global Constraints
CPU only; offline inference; no cloud key or new model download; no .env/credential ingestion; no fabricated database counts; preserve all existing work.

## Review Focus
- A project reference must not override a real data/count request.
- Project explanation keywords must not trigger SQL, product-vector search or user document retrieval.
- Follow-ups should use project context without dragging unrelated questions into it.
- Missing model/service should leave factual project help accessible.
- Secret environment values must never enter project context.

### Task 1: Project context
Files: engines/project_knowledge.py, docs/assistant-project-guide.md, tests/test_project_chat.py.
- [x] Write and run failing intent/context tests.
- [x] Implement is_project_question(query) and get_project_context(query), reading only the fixed guide path and safe configuration fields.
- [x] Run tests green.

### Task 2: Conversational routing
Files: engines/rag_orchestrator.py, tests/test_project_chat.py.
- [x] Write and run failing project-route, fallback and follow-up tests.
- [x] Add a grounded project explanation route with sources; strengthen the general system prompt to keep normal topics natural and avoid unsupported tool/live-data claims.
- [x] Run project, image, general, data and upload regression tests.

### Task 3: Verify and document
Files: README.md.
- [x] Document example general/project/data questions and offline model limits.
- [x] Obtain static review, resolve concrete issues, restart and test live general/project/follow-up requests.
- [x] Record evidence and leave working changes in the existing IDE checkout, without committing or publishing.


## Verification record
- Full relevant suite: 122 tests passed (project, image, document, general chat, conversation, upload, frontend, master-brand and dashboard).
- After the welcome addition: all 37 frontend contract tests passed.
- Static review found polite catalog and uploaded-document paraphrase routing cases; five failing reproductions were added, fixes passed, and the reviewer confirmed no outstanding blockers.
- Live HTTP general question about rainbows returned a normal answer with no fabricated data sources (31.7 seconds).
- Live Hinglish project-working question returned grounded Flask/Ollama project information and guide/config source filenames (49.4 seconds).
- Live database follow-up used conversation context and explained MySQL preference with SQLite fallback (48.2 seconds). An observed language-mixing issue prompted moving verified context first and the latest question/language instruction last.
- After that prompt change: all 30 project/conversation tests passed. Final live explicit English project architecture request returned a clear two-sentence English answer with real guide/config sources (40.8 seconds).
- Ollama runtime reported llama3.2 with size_vram=0. No cloud model, GPU or additional model download was introduced by this follow-up.
- App restarted with the final code. Existing image functionality, deployment instructions and PD Comparison Studio rename preserved. No commit or publication requested.
