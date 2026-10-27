# ABC SmartPath

Helping people find suitable training—and helping staff follow up with the right context.

SmartPath is a working interview prototype for a fictional training company. It combines AI course guidance, an optional skills challenge and a staff workspace in one application. The idea is to make choosing a course easier and give staff a clearer starting point for a useful follow-up conversation.

**Status:** the local prototype has been exercised. This repository adds a hosting configuration, but the public deployment and live cloud-AI integration have not yet been verified. There is no public URL to use yet.

## What you can do

**As a visitor**

- Browse the sample course catalogue, including prices, formats and prerequisites.
- Describe what you want to learn, answer guided questions or ask about course policies.
- See course recommendations with explanations and source references.
- Try a short Python, AI-at-work or Excel skills challenge. Feedback suggests a starting point; it is not a qualification or a validated placement assessment.
- Submit an enquiry with service-contact consent, separately from marketing consent.

**As a member of staff**

- Open enquiries with the original customer message and training requirements.
- Record a next action, update the enquiry status and schedule a service reminder.
- Write a reply or ask AI to prepare a draft, then review, edit, approve or reject it.
- Find approved messages in the outbox and open them in an email application.
- Record confirmed paid bookings and inspect the resulting metrics.

Public visitors do not need the staff token. Everyone using the shared staff token has the same dashboard permissions; this prototype does not provide individual staff accounts.

## How it works

1. The training guide interprets the visitor’s request and asks for missing information.
2. Retrieval searches the approved sample course and FAQ content.
3. Application rules check level, prerequisites, delivery format, budget, dates and capacity.
4. The language model explains the eligible options using the supplied information.
5. If the visitor submits an enquiry, SQLite stores it for staff follow-up.
6. Staff review commercial drafts before they enter the application outbox.

When the requirements cannot be met, the application can explain the mismatch and offer a human-help enquiry. It does not invent a course or automatically relax the learner’s requirements.

## Technology

| Component | Role |
| --- | --- |
| React, Vite and Tailwind CSS | Customer pages, skills challenge and staff workspace |
| FastAPI and Pydantic | API routes, validation and access checks |
| LangGraph | Bounded conversational workflow with read-only agent tools |
| BM25 and MiniLM embeddings | Keyword and semantic retrieval |
| Reciprocal rank fusion and a cross-encoder | Combine and rerank retrieved candidates |
| SQLite | Catalogue facts, sessions, enquiries, drafts, reminders and outbox records |
| Ollama | Runs the local Qwen model during local development |
| Ollama Cloud adapter | Prepared option for hosted inference; requires credentials and a verified available model |
| H5P Standalone | Self-hosted true/false activities with feedback |

The retrieval system selects information; the language model uses that information to write a response. Enquiry records do not automatically retrain the model. Codex assisted with implementation and debugging; that assistance does not replace testing or review.

## Run locally

These instructions target macOS with Python 3.11, Node.js 22 with npm, and Ollama installed. Initial setup downloads dependencies and retrieval models. Ensure those commands are available in your terminal before starting.

From the repository’s root directory:

```sh
bash scripts/setup.sh
ollama pull qwen3:4b-instruct-2507-q4_K_M
bash scripts/start.sh
```

Setup generates a local `.env` file with a random staff token. Leave Ollama running. Open <http://127.0.0.1:5173> for the website and <http://127.0.0.1:8000/api/health> for the API and AI status. Press Control+C in the application terminal to stop it.

The local launcher runs the frontend, backend and reminder worker. It retains the SQLite database across restarts. The `127.0.0.1` addresses work only on the computer running the application.

## Public hosting

The hosted configuration builds the existing frontend and serves it alongside FastAPI from one public origin. It does not expose a Vite development server or depend on the developer’s laptop remaining on.

- [Dockerfile.hosted](Dockerfile.hosted) builds the frontend and Python service.
- [render.yaml](render.yaml) proposes a single Render service with a persistent disk.
- [.env.hosted.example](.env.hosted.example) documents the required hosted settings, without credentials.
- [Hosting guide](docs/HOSTING.md) covers configuration and release checks.

**Do not treat the hosting configuration as a completed deployment.** The current Render configuration proposes paid resources; review the current cost before creating them. The hosted AI model must be available from the provider and tested. The local Qwen model is not assumed to be available through the cloud endpoint.

## Verification

In the hosting preparation checkout on 27 October 2026:

| Check | Result |
| --- | --- |
| Backend tests | 74 passed |
| Frontend tests | 28 passed |
| Frontend production build | Passed |
| Linux Docker build | Not run; Docker unavailable in the authoring environment |
| Public deployment | Not completed |
| Live hosted AI and external-device journey | Not tested |

Backend workflow tests use explicit AI/retrieval test doubles. Cloud-adapter tests mock the HTTP response. Frontend tests mock API responses and selected H5P events. These checks verify particular behaviours; they do not establish AI answer quality, production readiness or revenue improvement.

To run the application checks after local setup:

```sh
bash scripts/test.sh
```

To exercise the actual neural retrieval models separately:

```sh
PYTHONPATH=backend HF_HOME="$PWD/.hf-cache" .venv/bin/python scripts/evaluate_rag.py
```

That evaluation uses a small sample set, so it should not be presented as broad evidence of retrieval quality.

## Important limits

- Courses, prices, dates, capacities and policies are sample inventory. There are no real ABC commercial results.
- The payment button is a clearly labelled demonstration. It takes no payment and creates no payment-confirmed booking.
- Approved replies and reminders enter the application outbox. SmartPath does not deliver external email or confirm delivery from the user’s email application.
- Paid-booking metrics depend on staff-entered records; a payment gateway does not verify them.
- The optional machine-learning experiment uses synthetic labels. Its score is not a validated probability of conversion and does not set operational priority.
- Quiz questions and automated feedback have not been reviewed by subject experts. There is no countdown or public leaderboard; the colourful mascots can be hidden.
- Hosting adds request-size and rate limits, including a shared daily public-chat ceiling of 100 messages. This is a demonstration limit, not unlimited public capacity.
- Security, accessibility, load testing, independent AI evaluation and production operations need further work before real customer use.

A real pilot would compare paid-booking conversion, revenue per lead and incremental contribution after costs, alongside recommendation quality, response speed and successful staff handoff. No uplift is claimed here.

## Project layout

```text
backend/app/       API, agent, retrieval, catalogue, storage and hosting entry point
backend/tests/     Backend and hosting regression checks
frontend/src/      React interface and interaction tests
frontend/public/   H5P activities, sample questions and mascot assets
scripts/           Local setup, startup, tests and retrieval evaluation
docs/              Hosting, verification and quiz notes
Dockerfile.hosted  Combined hosted application image
render.yaml        Proposed Render deployment configuration
```

## Credentials and data

Keep `.env`, API keys, staff tokens, databases and real enquiry records out of Git. The repository contains configuration examples rather than working credentials. Hosted inference sends relevant request/context data to the configured cloud provider; assess data handling before using real customer information.

The repository is intended to be private. A public website does not require its source code or staff dashboard to be public.

## Third-party components

H5P Standalone and its bundled libraries retain their licences and notices under `frontend/public/h5p-player/` and `frontend/public/h5p/`. The sample questions were written for this prototype and are not an expert-certified question bank. Dependency and model licences should be reviewed before commercial reuse.
