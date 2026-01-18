# safe-journalist

Minimal Python hello-world for calling the **Maple enclave API directly** (no proxy).

This reimplements the bare minimum of the OpenSecret flow:
- `GET /attestation/{nonce}`
- `POST /key_exchange`
- Encrypt/decrypt request/response bodies for `/v1/chat/completions`

## Features

### 🌐 Web Frontend

Simple, clean web interface for non-technical users to test the system without using curl or CLI commands.

**Access at**: `http://localhost:8000/` (after starting the server)

**Features:**
- Create entries with textarea form
- View real-time status (entries count, summaries count, trigger info)
- View latest alert summary
- Manual summarization trigger
- Recent entries list (last 5)
- Mobile-responsive design
- Auto-refresh after actions

### 🎙️ Local Speech-to-Text (Audio Entries)

Send an audio clip and have it transcribed **locally** (no cloud STT) and stored as a normal entry.

- Endpoint: `POST /entries/audio` (multipart form field `file`)
- Default model: `nvidia/parakeet-tdt-0.6b-v3`
- Override: set `STT_MODEL` to a Parakeet ASR model id (NeMo pretrained). Examples:
  - `nvidia/parakeet-tdt-0.6b-v3`
  - `nvidia/parakeet-ctc-0.6b`
  - `nvidia/parakeet-rnnt-0.6b`
- Install deps: `uv sync --extra stt`

### 🤖 Automatic AI Summarization

Every 3rd entry automatically triggers an encrypted AI call that generates a concise summary of all entries. Perfect for emergency contacts who need actionable information without reading dozens of individual check-ins.

**How it works:**
- After the Nth entry (default: 3), summarization triggers automatically
- AI analyzes the previous summary + new entries since that summary
- Generates 3-5 bullet points with actionable information
- All data encrypted end-to-end via Maple's secure enclave

## Setup

Create a `.env` file in the project root (optional):

```bash
# .env
MAPLE_API_KEY=your-maple-api-key-here
DATA_DIR=./data
MAPLE_API_URL=https://enclave.trymaple.ai
MAPLE_MODEL=llama-3.3-70b
SUMMARY_TRIGGER_COUNT=3
```

The server automatically loads this file on startup.

## Quick Start

### 1. Configure Environment (Optional)

Create a `.env` file in the project root:
```bash
MAPLE_API_KEY=your-key-here  # Optional, only needed for AI summarization
DATA_DIR=./data
```

Or export variables manually (will override `.env`):
```bash
export MAPLE_API_KEY="your-key"
export DATA_DIR="./data"
```

### 2. Start the Server
```bash
uv run uvicorn safe_journalist.api:app --reload --port 8000
```

The server automatically loads `.env` file if present.

### 3. Use the Web Interface

Open your browser to **http://localhost:8000/**

The web interface provides:
- ✅ Entry creation form
- ✅ Status dashboard
- ✅ Alert viewer
- ✅ Recent entries list
- ✅ Manual summarization trigger

### 4. Or Use the API Directly

#### Create Entries
```bash
curl -X POST http://127.0.0.1:8000/entries \
  -H "content-type: application/json" \
  -d '{"text":"Arrived at protest. 200+ people. Police present."}'
```

#### List Recent Entries
```bash
curl http://127.0.0.1:8000/entries?limit=5
# Returns: array of recent entries with timestamp and preview
```

#### Check Status
```bash
curl http://127.0.0.1:8000/status
# Returns: entries count, summaries count, trigger threshold
```

#### Get Latest Alert
```bash
curl http://127.0.0.1:8000/alert
# Returns: latest summary with timestamp
```

#### Manual Summarization
```bash
curl -X POST http://127.0.0.1:8000/summarize
# Useful for testing or forcing a summary before threshold
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DATA_DIR` | `/data` | Base directory for storing entries and summaries |
| `SUMMARY_TRIGGER_COUNT` | `3` | Number of entries before auto-summarization triggers |
| `MAPLE_API_KEY` | - | **Required** for summarization. API key for Maple enclave |
| `MAPLE_API_URL` | `https://enclave.trymaple.ai` | Maple enclave endpoint |
| `MAPLE_MODEL` | `llama-3.3-70b` | AI model to use for summarization |

## Data Structure

```
data/
├── entries/
│   ├── 20260117T110000Z-entry.md
│   ├── 20260117T120000Z-entry.md
│   └── 20260117T130000Z-entry.md
└── summaries/
    └── 20260117T135000Z-summary.md
```

## Demo

Run the included demo script to see auto-summarization in action:

```bash
# Start the API server first (reads from .env automatically)
# Or set variables temporarily:
DATA_DIR=./demo-data uv run uvicorn safe_journalist.api:app

# In another terminal, run the demo
./demo_test.sh
```

The demo creates 3 entries, triggers automatic summarization, and displays the AI-generated summary.

## Documentation

- **[docs/solutions/](docs/solutions/)** - Structured documentation of solved problems with search tags
- **[docs/features/](docs/features/)** - Feature planning and review documents
- **[docs/PRODUCT_BRIEF.md](docs/PRODUCT_BRIEF.md)** - Product overview

## Notes
- Hackathon mode: this script **extracts** the server public key from the attestation document but does **not** fully verify attestation.
- If Maple changes the attestation document format, `_extract_public_key_from_attestation()` may need adjustment.
