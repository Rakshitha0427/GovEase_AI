# GovEase AI

A conversational government services assistant MVP. The app includes scheme discovery, criteria-based eligibility guidance, application guidance, English/Hindi/Kannada response preferences, PDF extraction, and source references in one chat interface.

## Run locally

1. Install Node.js 18+ and Python 3.10+.
2. Install frontend packages: `npm install`
3. Install backend packages: `python -m venv .venv` then activate it and run `pip install -r requirements.txt`.
4. Create a root `.env` file next to `package.json`. Set `GEMINI_API_KEY` for Gemini and configure `MONGODB_URI` with your MongoDB Atlas connection string. Set `MONGODB_DATABASE=govease`; `GEMINI_MODEL` defaults to `gemini-3.5-flash-lite`. Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS; it defaults to false for local development. Keep `.env` private (it is gitignored). Without a non-empty Gemini key, the backend uses deterministic demo responses; without a Mongo URI, guest chat and PDF extraction still work, while accounts and persistent history return a configuration error.
5. Start the API: `uvicorn backend.main:app --reload --port 8000`
6. In a second terminal start the UI: `npm run dev`.

The Vite server proxies `/api` to the FastAPI server. API documentation is available at `/docs`.

When you add or change `.env`, restart the FastAPI server so it reloads the configuration. The API key is read only by the backend and is never sent to the React application. If Gemini is configured but the provider call fails or returns an empty response, the API returns a generic error rather than silently switching to demo output.

## Accounts and persistent history

Create a MongoDB Atlas cluster and database user, allow the development machine's IP address, then place the Atlas connection URI in the backend-only `MONGODB_URI` setting in `.env`. The application creates required collections and indexes on first account use. Passwords are stored as scrypt hashes; session tokens are random, stored only as hashes, and issued in HttpOnly cookies. Conversation queries are scoped to the signed-in user's ID. Uploaded PDF files are not stored.

Install the test-only dependency with `pip install -r requirements-dev.txt`, then run `python -m unittest backend.test_accounts backend.test_gemini -v`. Account and history tests use an in-memory MongoDB mock and do not need an Atlas URI.

## Data and accuracy

The bundled catalog is intentionally small, for demonstration only. It contains links to official sources but does not imply that the catalog is exhaustive or freshly verified. Always confirm current criteria, dates, and application steps with the linked authority. The assistant's eligibility assessment is informational and is not an approval decision.

MongoDB, authentication, persistent conversations, live government-site crawling, a production RAG corpus, OCR for scanned PDFs, and voice interaction are extension points, not configured services in this MVP. No user documents or personal details are persisted.
