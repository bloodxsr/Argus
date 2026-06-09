# Checkpoint 0008 - MERN Website Scaffold

## Status

Converted the website direction into MERN-style scaffolds for the Test Website and Report / Result Website.

## What Changed

- Added MERN runbook: `MERN_WEBSITE_PLAN.md`.
- Added Test Website MERN scaffold:
  - React/Vite client
  - Express API
  - Mongo replay session model
  - Security AI proxy endpoints
  - TypeScript contract shapes
- Added Report Website MERN scaffold:
  - React/Vite client
  - Express API
  - Mongo incident report model
  - report generation endpoints
  - TypeScript contract shapes
- Kept the Python Security AI service as the core decision engine.
- Made `index.html` the Vite React entry point in each website.
- Preserved earlier standalone pages as `static-prototype.html`.

## Why It Changed

The websites should use the MERN stack, while security reasoning, model inference, policy checks, and future telemetry agents remain outside the web stack.

## Validation

Passed on 2026-06-09:

```text
python -m unittest discover -s tests
Ran 17 tests
OK
```

Package JSON syntax check passed:

```text
test-website/package.json -> argus-test-website
report-website/package.json -> argus-report-website
```

Node/npm note:

```text
node: not found
npm: not found
```

The MERN apps cannot be installed or run on this machine until Node.js and npm are available.

## Relevant Notes

- [[Project Outcomes and Implementation Plan]]
- [[Shared_Contracts]]
- [[Project_checkpoints/0007_static_demo_websites]]

## Relevant Files

- `MERN_WEBSITE_PLAN.md`
- `test-website/package.json`
- `test-website/server/index.js`
- `test-website/src/main.jsx`
- `report-website/package.json`
- `report-website/server/index.js`
- `report-website/src/main.jsx`

## Next Step

Install Node.js/npm, run `npm install` in both website directories, and smoke-test the React/Express apps against the running Python Security AI API.
