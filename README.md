# GovEase AI

A conversational government services assistant MVP. The app includes scheme discovery, criteria-based eligibility guidance, application guidance, English/Hindi/Kannada response preferences, PDF extraction, and source references in one chat interface
GovEase AI is a conversational assistant that helps people explore Indian government schemes, understand published eligibility criteria, and find next steps for applying. It combines a React chat interface with a FastAPI backend, a bundled scheme catalog, and optional Gemini responses. People can try the assistant as guests; signing in enables account settings and saved conversations.

- **Live application:** [gov-ease-ai-n3p3.vercel.app](https://gov-ease-ai-n3p3.vercel.app)
- **GitHub repository:** [Rakshitha0427/GovEase_AI](https://github.com/Rakshitha0427/GovEase_AI)

## Problem and solution

Government scheme information can be difficult to find and compare, and application requirements can be spread across official sources. GovEase AI brings scheme discovery, informational eligibility guidance, application steps, source links, and document text extraction into a chat-oriented interface. Answers should be treated as guidance: users should confirm current requirements with the linked official authority, which makes final eligibility decisions.

## Features

- **Guest access and accounts:** Create an account or sign in with an email and password. Account creation requires a password of at least 10 characters. Guests can use chat without signing in.
- **Profile settings:** Signed-in users can update their display name and email address, and can sign out.
- **AI chat:** Ask about schemes, eligibility, application steps, or general questions. The UI offers English, Hindi, and Kannada response preferences. With `GEMINI_API_KEY` configured, the backend sends prompts to the Gemini API; without it, the app uses deterministic demo responses based on the bundled catalog.
- **Scheme catalog and references:** The backend searches the bundled `backend/schemes.json` catalog and returns matching official-source references. The catalog is a small demonstration dataset, not a live or exhaustive government database.
- **Persistent chat history:** Signed-in conversations and messages are saved in MongoDB. Users can reopen, rename, and delete their conversations. The history list is limited to the latest 100 conversations.
- **Conversation continuation:** Opening a saved conversation restores its messages. New replies are associated with that conversation, and recent messages are supplied as context to the assistant.
- **PDF upload and extraction:** Upload a PDF for selectable text extraction and chat-based discussion. Extracted text is sent with the chat request; the uploaded file itself is not saved. Uploads are limited to 10 MB by default. Scanned PDFs are not OCR processed.
- **Responsive chat interface:** Start a new conversation, use suggested prompts, and view assistant source links in the chat.

## Technologies

- **Frontend:** React 18, Vite 6, JavaScript, Tailwind CSS, Lucide icons
- **Backend:** Python, FastAPI, Uvicorn, Pydantic
- **Database:** MongoDB Atlas (via PyMongo) for accounts, sessions, and conversation history
- **AI:** Google Gemini API via the Google Gen AI Python SDK; deterministic demo responses are available when no Gemini key is configured
- **PDF processing:** PyMuPDF for local text extraction
- **Deployment configuration:** Vercel for the Vite frontend and Render for the FastAPI service

## Application architecture

```text
Browser (React + Vite)
  ├─ /api requests ── local Vite proxy ──> FastAPI (Python)
  └─ /api requests ── VITE_API_BASE_URL ──> FastAPI (deployed)
                                            ├─ Gemini API (when configured)
                                            ├─ bundled backend/schemes.json catalog
                                            ├─ PyMuPDF (extract PDF text in memory)
                                            └─ MongoDB Atlas (accounts, sessions, chats)
```

The frontend communicates with the API using `src/api.js`. FastAPI serves chat, scheme search, document extraction, authentication, and conversation endpoints. Authentication uses an HttpOnly session cookie; passwords are stored as scrypt hashes and session tokens are stored as hashes. Conversation and message queries are scoped to the signed-in user's account. Uploaded PDF files are processed in memory and are not stored. In local development Vite proxies `/api` to `http://localhost:8000`; in a deployed frontend, `VITE_API_BASE_URL` points to the backend origin.

## Project structure

```text
GovEase_AI/
├── backend/
│   ├── auth.py                 # Signup, login, logout, profile, cookie sessions
│   ├── database.py             # MongoDB connection and indexes
│   ├── history.py              # Per-user conversation and message persistence
│   ├── main.py                 # FastAPI app, chat, scheme search, PDF extraction
│   ├── schemes.json             # Bundled demonstration scheme catalog
│   ├── security.py              # Password and session-token hashing
│   ├── test_accounts.py         # Account and conversation tests
│   └── test_gemini.py           # Gemini and demo response tests
├── src/
│   ├── features/
│   │   ├── account/             # Auth modal, profile, account menu and styles
│   │   └── history/             # Saved conversation list and controls
│   ├── App.jsx                  # Main chat interface and client state
│   ├── api.js                   # API base URL and credentialed fetch helper
│   ├── main.jsx                 # React application entry point
│   └── styles.css               # Application styles
├── index.html
├── package.json
├── requirements.txt
├── render.yaml                  # Render backend service configuration
├── vercel.json                  # Vercel frontend build configuration
├── vite.config.js               # Vite development server and API proxy
└── README.md
```

## Local installation and setup

### Requirements

- Node.js and npm
- Python 3.10 or newer
- A MongoDB Atlas connection string to enable accounts and persistent chat history
- A Gemini API key to enable Gemini-generated responses (optional; without it the backend uses demo responses)

### 1. Install frontend dependencies

From the repository root:

```bash
npm install
```

### 2. Create and activate a Python virtual environment

```bash
python -m venv .venv
```

Activate it, then install the backend requirements:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the repository root (beside `package.json`) and provide values for the settings you need. Use your own credentials locally; never commit the file.

```dotenv
# Optional: omit or leave empty to use deterministic demo responses
GEMINI_API_KEY=<your-gemini-api-key>
GEMINI_MODEL=<gemini-model-name>

# Required for signup, login, profile updates, and saved chat history
MONGODB_URI=<your-mongodb-atlas-connection-string>
MONGODB_DATABASE=govease

# Local frontend origins are allowed in development by default
APP_ENV=development
FRONTEND_ORIGINS=

# Defaults suitable for local HTTP development
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=lax
MAX_UPLOAD_MB=10
```

`GEMINI_MODEL` defaults to `gemini-3.5-flash-lite`, `MONGODB_DATABASE` defaults to `govease`, and `MAX_UPLOAD_MB` defaults to `10`. Account and conversation features require a reachable MongoDB database; chat and PDF extraction can be used without MongoDB when signed out. Never put backend credentials in `VITE_*` variables: Vite variables are included in the browser build. `.env` is gitignored.

### 4. Start the API and frontend

In one terminal, from the repository root:

```bash
uvicorn backend.main:app --reload --port 8000
```

In a second terminal:

```bash
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`). The development server proxies `/api` calls to FastAPI at port 8000. FastAPI's interactive API documentation is available at `http://localhost:8000/docs`.

## Environment variable reference

| Variable | Purpose | Default / notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | Backend-only credential for Gemini responses | Unset or empty enables demo responses |
| `GEMINI_MODEL` | Gemini model identifier | `gemini-3.5-flash-lite` |
| `MONGODB_URI` | MongoDB connection URI | Required for accounts and persistent history |
| `MONGODB_DATABASE` | MongoDB database name | `govease` |
| `VITE_API_BASE_URL` | Frontend API origin for deployed builds | Empty locally; Vite proxies `/api` |
| `APP_ENV` | Backend environment mode | `development`; production requires explicit frontend origins |
| `FRONTEND_ORIGINS` | Comma-separated allowed frontend origins | Local Vite origins are allowed in development; required in production |
| `SESSION_COOKIE_SECURE` | Require HTTPS for the session cookie | `false` locally; set `true` in production |
| `SESSION_COOKIE_SAMESITE` | Session cookie SameSite policy | `lax` locally; Render configuration uses `none` with Secure |
| `MAX_UPLOAD_MB` | Maximum PDF upload size in megabytes | `10` |

For a production setup, configure backend-only values in the backend host's environment settings. Set `VITE_API_BASE_URL` in the frontend build environment to the backend's HTTPS origin (without an `/api` suffix). The Render Blueprint sets production cookie settings and expects `FRONTEND_ORIGINS` to contain the deployed frontend origin. Keep Gemini and MongoDB credentials out of the frontend environment.

## Future improvements

- Expand and regularly verify the scheme catalog against official government sources.
- Add OCR support for scanned PDFs.
- Add broader automated coverage and end-to-end testing for the full signup-to-chat experience.
- Improve scheme matching and eligibility guidance while keeping the distinction between informational guidance and official decisions clear.
- Improve document handling and conversational controls as the application grows.
