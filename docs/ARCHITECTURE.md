# Safe Journalist Architecture

High-level overview of how the Safe Journalist app works.

## System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        USER[User/Client]
    end
    
    subgraph "API Layer (FastAPI)"
        API[POST /entries]
        BGT[Background Tasks]
    end
    
    subgraph "Trigger System"
        COUNT[Count Trigger<br/>≥N entries]
        TIMER[Time Trigger<br/>N seconds delay]
    end
    
    subgraph "Core Logic"
        STORAGE[Storage Module<br/>entries/ & summaries/]
        SUMMARIZER[Summarizer Module]
    end
    
    subgraph "Encryption Layer"
        SESSION[Session Manager<br/>MapleSession]
        CRYPTO[ChaCha20-Poly1305<br/>Encryption/Decryption]
    end
    
    subgraph "Maple AI Enclave"
        ATTEST[Attestation Service<br/>GET /attestation]
        KEX[Key Exchange<br/>POST /key_exchange]
        AI[AI Completion<br/>POST /v1/chat/completions]
    end
    
    subgraph "File System"
        ENTRIES[(entries/<br/>timestamp-entry.md)]
        SUMMARIES[(summaries/<br/>timestamp-summary.md)]
    end
    
    USER -->|POST text entry| API
    API -->|Write entry| STORAGE
    STORAGE -->|Save to disk| ENTRIES
    
    API -->|Check count| COUNT
    API -->|Schedule/reset timer| TIMER
    
    COUNT -->|≥N entries<br/>immediate| BGT
    TIMER -->|After delay<br/>no new entries| BGT
    
    BGT -->|Trigger summarization| SUMMARIZER
    
    SUMMARIZER -->|Read previous summary| STORAGE
    SUMMARIZER -->|Read new entries| STORAGE
    STORAGE -->|Load from disk| ENTRIES
    STORAGE -->|Load from disk| SUMMARIES
    
    SUMMARIZER -->|Get session| SESSION
    SESSION -->|1. Request attestation| ATTEST
    ATTEST -->|Attestation doc +<br/>server public key| SESSION
    SESSION -->|2. Exchange keys| KEX
    KEX -->|session_id +<br/>session_key| SESSION
    
    SUMMARIZER -->|Encrypt prompt| CRYPTO
    CRYPTO -->|Encrypted payload| AI
    AI -->|Encrypted response| CRYPTO
    CRYPTO -->|Decrypted summary| SUMMARIZER
    
    SUMMARIZER -->|Write summary| STORAGE
    STORAGE -->|Save to disk| SUMMARIES
    
    API -->|Return entry path| USER
```

## Data Flow: Entry Creation

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Storage
    participant Counter
    participant Timer
    participant BG as Background Task
    
    User->>API: POST /entries {"text": "..."}
    API->>Storage: write_entry(text, timestamp)
    Storage->>Storage: Save to entries/timestamp-entry.md
    Storage-->>API: entry_path
    
    API->>Counter: count_entries_since_last_summary()
    
    alt Count >= SUMMARY_TRIGGER_COUNT
        Counter-->>API: count=3 (threshold met)
        API->>Timer: Cancel pending timer
        API->>BG: Trigger summarization immediately
        Note over API,BG: Count-based trigger fires
    else Count < SUMMARY_TRIGGER_COUNT
        Counter-->>API: count=1 (below threshold)
        API->>Timer: Cancel existing timer
        API->>Timer: Schedule new timer (10s delay)
        Note over API,Timer: Time-based trigger scheduled<br/>(resets on each new entry)
    end
    
    API-->>User: 200 OK {"path": "...", "timestamp": "..."}
    
    Note over BG: Summarization runs in background<br/>(doesn't block response)
```

## Data Flow: AI Summarization

```mermaid
sequenceDiagram
    participant BG as Background Task
    participant Summarizer
    participant Storage
    participant Session
    participant Crypto
    participant Maple as Maple AI Enclave
    
    BG->>Summarizer: generate_summary()
    
    Summarizer->>Storage: get_latest_summary()
    Storage-->>Summarizer: last_summary, timestamp
    
    Summarizer->>Storage: get_entries_since_timestamp(timestamp)
    Storage-->>Summarizer: [entry1, entry2, ...]
    
    Summarizer->>Session: get_maple_session()
    
    Session->>Maple: GET /attestation/{nonce}
    Maple-->>Session: attestation_doc (server_public_key)
    
    Session->>Crypto: Encrypt client_public_key
    Session->>Maple: POST /key_exchange (encrypted)
    Maple-->>Session: session_id, session_key
    Session-->>Summarizer: MapleSession ready
    
    Summarizer->>Summarizer: Build prompt:<br/>Previous: {last_summary}<br/>New: {entries}<br/>Task: Generate summary
    
    Summarizer->>Crypto: encrypt_chacha20_poly1305(prompt)
    Crypto-->>Summarizer: encrypted_payload
    
    Summarizer->>Maple: POST /v1/chat/completions<br/>(encrypted payload + session_id)
    Maple-->>Summarizer: encrypted_response
    
    Summarizer->>Crypto: decrypt_chacha20_poly1305(response)
    Crypto-->>Summarizer: summary_text
    
    Summarizer->>Storage: write_summary(summary_text, timestamp)
    Storage->>Storage: Save to summaries/timestamp-summary.md
    Storage-->>Summarizer: summary_path
    
    Summarizer-->>BG: Done (logged)
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `/data` | Base directory for entries and summaries |
| `SUMMARY_TRIGGER_COUNT` | `3` | Trigger summarization after N entries |
| `SUMMARY_TRIGGER_DELAY` | `10` seconds | Trigger summarization after N seconds of inactivity |
| `MAPLE_API_URL` | `https://enclave.trymaple.ai` | Maple enclave API endpoint |
| `MAPLE_API_KEY` | (required) | API key for Maple service |
| `MAPLE_MODEL` | `llama-3.3-70b` | AI model to use for summarization |

## Key Components

### Storage Module (`storage.py`)
- Manages file I/O for entries and summaries
- Subdirectories: `entries/` and `summaries/`
- Timestamp-based filenames for ordering
- Helper functions for listing and counting

### Summarizer Module (`summarizer.py`)
- Orchestrates AI summarization flow
- Reads previous summary + new entries
- Constructs context-aware prompts
- Handles encrypted AI calls
- Writes summaries to disk

### Trigger System
- **Count-based**: Immediate trigger when threshold reached
- **Time-based**: Debounced timer (resets on each entry)
- Whichever fires first wins (other is cancelled)

### Encryption Layer
- **Session Management**: Attestation + key exchange
- **ChaCha20-Poly1305**: Symmetric encryption for requests/responses
- End-to-end encryption with AI enclave

## Security Model

```mermaid
graph LR
    subgraph "Safe Journalist"
        PLAIN[Plaintext Prompt]
    end
    
    subgraph "Encrypted Channel"
        ENC[ChaCha20-Poly1305<br/>Encrypted]
    end
    
    subgraph "Maple AI Enclave (TEE)"
        DECRYPT[Decrypt]
        AI[AI Model]
        ENCRYPT[Encrypt]
    end
    
    PLAIN -->|Session Key| ENC
    ENC -->|HTTPS| DECRYPT
    DECRYPT --> AI
    AI --> ENCRYPT
    ENCRYPT -->|HTTPS| ENC
    ENC -->|Session Key| PLAIN
    
    style ENC fill:#90EE90
    style DECRYPT fill:#FFB6C1
    style ENCRYPT fill:#FFB6C1
```

**Key Properties:**
- Attestation verifies enclave identity (hackathon mode: extracts public key)
- Session key negotiated via Diffie-Hellman
- Only encrypted data leaves the client
- AI processing happens in trusted execution environment (TEE)
