# 🎙️ ClickUp Voice Assistant

A web-based tool that lets you manage your ClickUp workspace using natural speech. Press a button, speak your intent, and the system translates your voice into concrete ClickUp operations — creating tasks, setting deadlines, assigning priorities, and more.

> *"Create a new task called API integration in the Backend sprint, set the priority to high, deadline is May 5th, and assign it to John."*

---

## ✨ Features

- **Voice-to-Task Creation** — Speak naturally to create tasks with names, descriptions, priorities, due dates, assignees, and tags
- **Update & Manage Tasks** — Modify existing tasks, set statuses, add comments, and reassign by voice
- **Deadline & Timeline Management** — Set, adjust, or remove deadlines using natural language ("push the deadline back two weeks")
- **Relative Date Resolution** — Understands "tomorrow," "next Tuesday," "end of next week," and more
- **Batch Operations** — A single voice command can produce multiple operations at once
- **Confirmation Preview** — Review and edit all operations before they're executed in ClickUp
- **Clarification Prompts** — Asks follow-up questions when the request is ambiguous or incomplete
- **Workspace Context** — Aware of your spaces, folders, lists, members, and statuses for accurate mapping
- **Session Management** — Conversational context is maintained within a session for follow-up commands

---

## 🏗️ Architecture

```
┌──────────────┐     ┌────────────────┐     ┌───────────────┐     ┌──────────────┐
│   Browser    │────▶│  FastAPI Server │────▶│  DeepSeek LLM │────▶│  ClickUp API │
│  (Frontend)  │     │                │     │  (Interpreter) │     │              │
│  Audio + UI  │◀────│  Whisper STT   │     │  Tool Calling  │     │  CRUD Ops    │
└──────────────┘     └────────────────┘     └───────────────┘     └──────────────┘
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | HTML / CSS / Vanilla JS | Audio capture, waveform UI, operation preview |
| **Speech-to-Text** | faster-whisper (local) | Transcribes audio to text |
| **LLM Interpreter** | DeepSeek (OpenAI-compatible) | Parses intent into structured tool calls |
| **Execution** | ClickUp REST API v2 | Creates/updates tasks, deadlines, and more |

---

## 📁 Project Structure

```
ClickupHelper/
├── run.py                        # Application entry point
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (not committed)
├── static/                       # Frontend assets
│   ├── index.html
│   ├── css/styles.css
│   └── js/
│       ├── app.js                # Main app logic
│       ├── api-client.js         # Backend API calls
│       ├── audio-recorder.js     # Microphone capture & recording
│       └── ui-manager.js         # UI state management
└── backend/
    └── app/
        ├── config.py             # Settings via pydantic-settings
        ├── main.py               # FastAPI app & lifespan
        ├── models/
        │   ├── operations.py     # Operation type enums
        │   └── schemas.py        # Request/response Pydantic models
        ├── routes/
        │   ├── audio.py          # /api/transcribe
        │   ├── interpret.py      # /api/interpret, /api/clarify
        │   ├── execute.py        # /api/execute
        │   └── session.py        # /api/session
        ├── services/
        │   ├── clickup_service.py    # ClickUp API client
        │   ├── llm_service.py        # DeepSeek LLM integration
        │   ├── session_service.py    # In-memory session store
        │   └── stt_service.py        # Whisper transcription
        └── utils/
            └── date_utils.py         # Relative date resolution
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- A **ClickUp account** with an API token
- A **DeepSeek API key** (or any OpenAI-compatible LLM endpoint)

### 1. Clone the Repository

```bash
git clone https://github.com/Hzhao-ocad/ClickupHelper
cd ClickUpVoiceAssistant
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `faster-whisper` requires [FFmpeg](https://ffmpeg.org/download.html) to be installed and available on your system PATH.

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# ClickUp
CLICKUP_API_TOKEN=pk_your_clickup_api_token
DEFAULT_CLICKUP_LIST_ID=your_default_list_id

# DeepSeek (OpenAI-compatible LLM)
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# Whisper (Speech-to-Text)
WHISPER_MODEL_SIZE=large-v3
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
```

### 5. Run the Application

```bash
python run.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check |
| `POST` | `/api/session` | Initialize a new session & fetch workspace context |
| `POST` | `/api/transcribe` | Upload audio and receive a transcript |
| `POST` | `/api/interpret` | Send transcript → get parsed operations or clarification questions |
| `POST` | `/api/clarify` | Answer clarification questions and get updated operations |
| `POST` | `/api/execute` | Approve and execute operations against ClickUp |

---

## 🎯 Supported Operations

The LLM can interpret voice commands into the following ClickUp operations:

| Operation | Description |
|-----------|-------------|
| `create_task` | Create a new task with name, description, list, priority, due date, assignee, tags |
| `update_task` | Update an existing task's fields |
| `set_due_date` | Set or change a task's deadline |
| `set_priority` | Set task priority (urgent, high, normal, low) |
| `assign_task` | Assign a task to a team member |
| `add_comment` | Add a comment to a task |
| `create_calendar_event` | Create a calendar event |
| `update_calendar_event` | Modify an existing calendar event |

---

## 🛠️ Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **LLM:** [DeepSeek](https://platform.deepseek.com/) (OpenAI-compatible API with tool calling)
- **Speech-to-Text:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (local Whisper inference)
- **HTTP Client:** [httpx](https://www.python-httpx.org/) (async ClickUp API calls)
- **Settings:** [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) with `.env` support
- **Frontend:** Vanilla HTML/CSS/JS (no build step required)

---

## ⚙️ Configuration

All settings are loaded from the `.env` file. Key options:

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL_SIZE` | `large-v3` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `WHISPER_DEVICE` | `cpu` | Compute device (`cpu` or `cuda` for GPU) |
| `WHISPER_COMPUTE_TYPE` | `int8` | Quantization (`int8` for CPU, `float16` for GPU) |
| `DEEPSEEK_TEMPERATURE` | `0.1` | LLM sampling temperature (lower = more deterministic) |
| `DEEPSEEK_MAX_TOKENS` | `2000` | Max tokens in LLM response |
| `SESSION_TTL_MINUTES` | `60` | Session expiration time |
| `CLICKUP_RATE_LIMIT_DELAY_MS` | `200` | Delay between ClickUp API calls (ms) |

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request
