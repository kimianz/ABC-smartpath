# Optional skills challenge - 26 October 2026

## What is implemented

- Separate Skills challenge navigation button, plus a homepage entry and an invitation from the training guide when a learner is unsure of their experience.
- Three original six-question sample tracks: Python foundations, AI at work, and Excel/data basics. About six minutes is an estimate; there is no enforced timer.
- Actual locally hosted H5P Standalone 3.8.2 with the ready-made H5P True/False 1.6 question type. All runtime assets are local; no Moodle installation or paid H5P.com subscription is used.
- Large original colourful monsters within the optional quiz, a Hide mascots control, checked-question progress, answer explanations, a result summary and a review of all answers.
- Explicitly choosing a new course search carries the selected topic and suggested experience level. Returning to the original conversation without starting a new search preserves it. No required skill, course prerequisite or booking is confirmed by the score.
- Guided-finder progress counts actual core requirements, including team size only for team enquiries. Optional follow-up questions may still appear.
- Uncertain free-text answers at choice questions no longer get submitted as invalid enum values.

## Content and assessment limits

The H5P software is ready-made. These question sets are original demonstration content, not third-party expert-validated assessments. Subject-expert review is pending, and the interface says so. Answer feedback is automatic; no live expert reviews responses. Do not describe it as expert feedback.

The rule suggests foundations for fewer than five correct answers and exploring intermediate topics with an adviser for five or six. Six binary questions are guessable and cannot establish reliable placement. This threshold is unvalidated. A real assessment needs expert content review, representative learners, richer practical tasks, reliability checks and a justified score interpretation.

There is no pass/fail credential, admission decision or guaranteed eligibility. Existing course checks still apply. The suggested level is used only after an explicit customer action. These results do not prove a revenue or handling-time improvement.

## Data and message boundaries

Answers stay in component memory while the challenge is open and are cleared on leaving/reloading. No learner identity, external analytics or learning-record-store service is configured. This is not a server-verified examination or persistent learning-record system. The selected goal and suggested level enter the regular enquiry journey only if the learner chooses a new search and later submits an enquiry under its existing consent flow.

The H5P frame reports only boolean checked answers. React checks the message origin, source window, run identifier, topic and current question. Duplicate checked-answer events cannot replace the first response. Do not add arbitrary uploaded H5P packages without a separate content/trust review.

## Costs and sources

The locally hosted software has no licence subscription. Hosting, maintenance, content writing and expert review can still cost money. Hosted H5P.com and MoodleCloud are separate commercial services.

Player: https://github.com/tunapanda/h5p-standalone (3.8.2).
Question libraries: the repository's bundled H5P test package; original licences and notices retained. Its sample question was replaced, rather than reused as content. The downloaded archive SHA-256 and exact source are recorded in the implementation evidence.
H5P content type: https://h5p.org/true-false .

## Verification scope

68 backend tests and 28 frontend tests passed. The production frontend build passed. Automated backend tests use explicit AI doubles; frontend tests use mocked APIs and frame-message events.

A separate actual-browser check on an isolated database completed all 18 real H5P questions across the three tracks. Python included an intentionally incorrect answer and produced 5/6 with the expected practice topic. AI and Excel produced 6/6. The check exercised explanations, progress, final results, the explicit new-search handoff, the chatbot's uncertain-level invitation, and a 390-pixel-wide layout with no horizontal overflow. No existing customer database was modified. No external email or payment was sent. This check did not evaluate live Qwen response quality, real expert validity, commercial impact, or production load.

The standalone Offline demo retains the original scripted customer-to-staff example. It does not contain the new H5P challenge. Quiz screenshots in the presentation are a separate visual fallback; do not present them as live interaction.

## Run the update

Restart the existing SmartPath backend with the normal startup script and refresh the browser. The frontend uses local static assets and does not need a new npm dependency. Preserve .env and backend/data when applying the update.
