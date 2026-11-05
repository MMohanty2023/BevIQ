# ChatGPT-Style General Assistant

## Intent

BevIQ should support normal conversation in addition to beverage-data work. Users should be able to greet it, ask general questions, understand jokes, continue follow-up conversations, and switch naturally between English and Roman Hinglish.

## Goals

- Route non-catalog questions to the local Ollama assistant.
- Preserve recent conversation context for follow-up questions.
- Match the latest user message: English replies in English, Roman Hinglish replies in Roman Hinglish, and Devanagari Hindi replies in Hindi.
- Keep beverage, database, UPC, upload, and comparison questions on verified application routes.
- Provide useful local fallback responses when Ollama is unavailable.

## Non-goals

- Add a paid hosted ChatGPT/OpenAI dependency.
- Invent beverage-data answers when the database has not supplied verified context.
- Replace existing dashboard, upload, or export behavior.

## Approach

Use the existing hybrid architecture: Ollama handles open-ended natural conversation; the orchestrator keeps catalog/document routing separate and supplies conversation history plus a language instruction. Local fallback handlers cover common greetings, jokes, help, and basic general questions when Ollama is unavailable.

## Verification

Add or update routing tests for casual English chat, Roman Hinglish chat, jokes, follow-up context, and protection against accidental catalog queries. Run the focused tests and then the full project test suite.
