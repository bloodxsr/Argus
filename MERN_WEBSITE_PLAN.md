# MERN Website Plan

## Overview

Argus uses MERN for the two website surfaces and keeps the Security AI / agent layer in Python and future Rust services.

```text
Test Website MERN       Report Website MERN
        |                       |
        v                       v
     Express APIs  --------  MongoDB histories
        |
        v
Python Security AI API
```

## Test Website

Path: `test-website/`

Purpose:
- launch synthetic scenarios
- show pipeline state
- proxy scenario runs to the Python Security AI API
- persist replay history in MongoDB

Ports:
- React/Vite: `5173`
- Express: `4100`

## Report Website

Path: `report-website/`

Purpose:
- generate incident reports from scenario replays
- show decision, action, confidence, and human review state
- persist report snapshots in MongoDB

Ports:
- React/Vite: `5174`
- Express: `4200`

## Runtime Order

1. Start MongoDB.
2. Start the Python Security AI service:

```bash
python -m uvicorn security_ai_service.api:app --host 127.0.0.1 --port 8000
```

3. Start the test website:

```bash
cd test-website
cp .env.example .env
npm install
npm run dev
```

4. Start the report website:

```bash
cd report-website
cp .env.example .env
npm install
npm run dev
```

## Contract Rule

The Python service remains the source of truth for behavior. The JSON schemas in `contracts/` remain the source of truth for payload shape. The TypeScript files in each website should be regenerated or manually kept aligned when contracts change.

## Current Environment Note

This machine does not currently have `node` or `npm` installed, so the MERN apps were scaffolded but not installed or executed here.
