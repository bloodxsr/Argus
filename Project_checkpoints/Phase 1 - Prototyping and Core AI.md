# Phase 1: Prototyping and Core AI

## Overview
This phase focused on establishing the foundational architecture of the project, including the initial Python AI service, standardized contracts, and the initial web surfaces. The goal was to build a runnable prototype that could be validated before integrating real models or live sensors.

## Key Milestones

### 1. Project Kickoff and Direction
- Defined the implementation blueprint and initial build artifacts.
- Established the requirement for a Python-based Security AI / LLM service, an evaluation harness, and a company constraint layer.
- Documented product outcomes, confirming a multi-repo architectural split (Test Website, Core Agent, Report Website).

### 2. Python Security AI Scaffold
- Implemented the first runnable Python AI service slice with structured contract objects for incidents, AI output, decisions, and constraints.
- Developed a heuristic-based decision engine with policy-aware enforcement, supported by an evaluation harness and unit tests.
- Introduced an Ollama-compatible reasoning shell as a fallback to heuristics, enabling retrieval-style context and layered inference.

### 3. Shared Contracts and Scenario Replay
- Created unified JSON schemas (`contracts/`) for events, incidents, risk scores, decisions, and action records to ensure consistency across microservices.
- Built a scenario replay pipeline (`scenarios/`) for deterministic testing of container, UEBA, and APT-style cases.

### 4. MERN Web Scaffold and UI/UX
- Developed the initial static prototype websites for scenario testing and reporting.
- Migrated the web layer to a MERN stack (MongoDB, Express, React/Vite, Node.js) while keeping the Python AI as the core decision engine.
- Outlined a massive UI/UX overhaul to introduce premium dark-mode aesthetics, glassmorphism, and dynamic animations.
