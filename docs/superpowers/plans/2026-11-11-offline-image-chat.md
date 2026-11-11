# Offline Image Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Describe photos and write related poetry offline on a CPU, with session-scoped follow-ups.
**Architecture:** A dedicated image engine owns validation, normalized image storage and local Ollama vision transport. The existing orchestrator retains conversation history and routes image requests before OCR/document/catalog logic.
**Tech Stack:** Flask, Pillow, SQLite, requests, Ollama qwen3-vl:2b-instruct.
**Spec:** docs/superpowers/specs/2026-11-11-offline-image-chat-design.md

## Global Constraints
No GPU or cloud inference. CPU options must be explicit. Model setup is an explicit download, never an automatic action from a chat request. Images stay within their conversation. Preserve PD Comparison Studio and existing document/catalog chat.

## Review Focus
- Photos without text must bypass OCR.
- Corrupt and huge images must fail without persisting broken uploads.
- Image IDs from other conversations must not disclose files.
- Missing models, busy CPU and timeouts must provide useful errors.
- General chat must not silently reuse an unrelated image.

### Task 1: Validated image persistence and CPU vision
Files: engines/image_chat.py, config.py, tests/test_image_chat.py.
- [x] Write failing tests for valid text-free photos, normalization, invalid files, ownership, CPU payload, history and model failures.
- [x] Run the new tests and observe the expected missing-module failure.
- [x] Implement ImageChatEngine.ingest(file_storage, session_id), get_image(session_id, image_id=None), answer(query, session_id, history=None, image_id=None, language_instruction='') and is_followup(query).
- [x] Run image engine tests to green.

### Task 2: Chat integration
Files: app.py, engines/rag_orchestrator.py, tests/test_image_chat.py.
- [x] Add failing tests proving image uploads bypass document OCR and image follow-ups use the saved session image.
- [x] Route supported image uploads to the image engine; use optional uploaded_image on route_and_execute.
- [x] Preserve ordinary conversation, language handling and catalog routes. Return service errors as 503 and invalid uploads as 400.
- [x] Run image, document, conversation and endpoint tests.

### Task 3: Offline deployment and verification
Files: .env.example, README.md.
- [x] Document CPU setup, one-time model download, environment settings, persistent storage and deployment resource limits.
- [x] Set num_gpu=0 for ordinary chat too.
- [x] Review the final diff; run relevant regression tests.
- [x] Restart the local app and run a real image-plus-poetry request. Verify response contents and CPU placement; report actual timing.

## Execution record
Existing branch: beverage_db. Preserve the existing template rename. Baseline: 24 upload, document and conversation tests passed. User's latest constraints settle the design: offline, CPU only, future CPU deployment. Implement in the existing IDE checkout so the running app receives the change. No commits or publication requested.


## Verification results
- Initial qwen3-vl:2b alias was the thinking variant; it exhausted 512 tokens with no final answer in a 129.9-second live request. Default changed to explicit qwen3-vl:2b-instruct (official instruct tag), without returning hidden reasoning to the user.
- Normalization defaults to a configurable 512-pixel edge to reduce CPU image-processing work.
- 97 targeted image, document, chat, conversation, frontend, master-brand and dashboard tests passed.
- Static reviewer identified document/photo routing, catalog count and natural follow-up cases; all were reproduced with failing tests and fixed. Final reviewer reported no outstanding blockers.
- Actual HTTP image upload returned a detailed cat description and a four-line poem in 90.0 seconds, with qwen3-vl:2b-instruct size_vram=0. CPU inference is functional, but this laptop is not instant.
- User data/source CSVs remain unchanged. Existing PD Comparison Studio rename preserved.
- Live follow-up without re-upload passed: HTTP200, same image_id, conversation_context_used=true, answer "The cat is ginger.", 74.6 seconds. Final changes loaded by app restart.
