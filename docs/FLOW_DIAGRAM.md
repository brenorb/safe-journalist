# Safe Journalist - High-Level Flow Diagram

This diagram provides a bird's-eye view of how the Safe Journalist application works, from user interaction to AI-powered summarization.

```mermaid
flowchart TB
    %% User Layer
    USER[👤 Journalist User]
    CONTACT[👥 Emergency Contact]
    
    %% Interface Layer
    WEB[🌐 Web Frontend<br/>index.html]
    API[⚡ FastAPI Server<br/>/entries, /alert, /status]
    
    %% Core Logic
    STORAGE[💾 Storage<br/>entries/ & summaries/]
    TRIGGER{🎯 Trigger?<br/>3 entries OR 10s delay}
    SUMMARIZER[🤖 AI Summarizer<br/>Context-aware prompts]
    
    %% External Services
    MAPLE[🔒 Maple AI Enclave<br/>Trusted Execution Environment]
    
    %% User interactions
    USER -->|Create entry| WEB
    USER -->|POST /entries| API
    WEB -->|REST API| API
    
    %% Entry flow
    API -->|Save entry| STORAGE
    API -->|Check trigger| TRIGGER
    
    %% Trigger logic
    TRIGGER -->|≥3 entries| SUMMARIZER
    TRIGGER -->|10s no activity| SUMMARIZER
    TRIGGER -->|<3 entries| STORAGE
    
    %% Summarization flow
    SUMMARIZER -->|Read entries + last summary| STORAGE
    SUMMARIZER -->|1. Attestation<br/>2. Key Exchange<br/>3. Encrypted Chat| MAPLE
    MAPLE -->|Encrypted Summary| SUMMARIZER
    SUMMARIZER -->|Save summary| STORAGE
    
    %% Alert retrieval
    CONTACT -->|View alert| WEB
    CONTACT -->|GET /alert| API
    API -->|Latest summary| STORAGE
    
    %% Styling
    classDef userClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef apiClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef storageClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef aiClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px
    
    class USER,CONTACT userClass
    class WEB,API apiClass
    class STORAGE,SUMMARIZER storageClass
    class MAPLE aiClass
```

## Key Components

### 👤 Users
- **Journalist**: Creates entries (text/audio) via web or API
- **Emergency Contact**: Views alerts and summaries when needed

### 🌐 Interface
- **Web Frontend**: Simple, mobile-responsive UI (`index.html`)
- **FastAPI Server**: REST endpoints for entries, alerts, status

### 💾 Storage
- **Entries**: Timestamped markdown files in `data/entries/`
- **Summaries**: AI-generated summaries in `data/summaries/`

### 🎯 Trigger System
- **Count-based**: Triggers after 3 entries (configurable)
- **Time-based**: Triggers after 10s of inactivity (configurable)
- Whichever fires first wins, other is cancelled

### 🤖 AI Summarizer
- Reads previous summary + new entries for context
- Generates 3-5 bullet actionable summary
- All communication encrypted end-to-end

### 🔒 Maple AI Enclave
- **Attestation**: Verifies enclave identity
- **Key Exchange**: Establishes session keys
- **Encrypted Chat**: Processes requests in Trusted Execution Environment (TEE)

## Flow Summary

1. **User creates entries** → API saves to disk
2. **Trigger system** monitors count (3 entries) or time (10s inactivity)
3. **When triggered** → Summarizer reads context (previous summary + new entries)
4. **Secure AI call** → End-to-end encrypted with Maple AI enclave (attestation → key exchange → encrypted chat)
5. **Summary saved** → Emergency contacts can access latest alert via web or API

## Security Model

All AI communication uses:
- ChaCha20-Poly1305 symmetric encryption
- Session keys negotiated via Diffie-Hellman
- Only encrypted data transmitted over network
- AI processing in Trusted Execution Environment (TEE)

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical diagrams and implementation details.
