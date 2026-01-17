# safe-journalist

Minimal Python hello-world for calling the **Maple enclave API directly** (no proxy).

This reimplements the bare minimum of the OpenSecret flow:
- `GET /attestation/{nonce}`
- `POST /key_exchange`
- Encrypt/decrypt request/response bodies for `/v1/chat/completions`

## Setup
```bash
cp .env.example .env
# edit .env
uv run safe-journalist
```

## Notes
- Hackathon mode: this script **extracts** the server public key from the attestation document but does **not** fully verify attestation.
- If Maple changes the attestation document format, `_extract_public_key_from_attestation()` may need adjustment.
# safe-journalist
