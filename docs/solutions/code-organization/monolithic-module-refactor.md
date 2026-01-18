---
title: "Refactoring Monolithic __init__.py into Focused Modules"
date: 2026-01-17
category: code-organization
severity: medium
tags:
  - refactoring
  - separation-of-concerns
  - module-architecture
  - python
components:
  - safe_journalist
status: resolved
related_issues: []
---

# Refactoring Monolithic __init__.py into Focused Modules

## Problem Symptom

The `src/safe_journalist/__init__.py` module contained mixed concerns with ~200+ lines handling:
- Maple session data models
- Attestation document decoding (COSE_Sign1 parsing)
- Cryptographic operations (ChaCha20-Poly1305 encryption/decryption)
- HTTP transport for key exchange and encrypted OpenAI calls
- CLI entry point with environment variable parsing

This violated separation of concerns and made the codebase difficult to maintain, test, and reason about.

## Investigation Steps

1. **Analyzed module responsibilities**: Identified 5 distinct concerns mixed in a single file
2. **Mapped dependencies**: Drew dependency graph to determine clean split points
3. **Identified behavioral contracts**: Documented exact algorithm flow to preserve during refactor
4. **Planned module boundaries**:
   - `crypto.py` → Base64 helpers and encryption primitives
   - `attestation.py` → COSE document parsing and public key extraction
   - `session.py` → Session data model and creation workflow
   - `client.py` → HTTP transport layer
   - `cli.py` → CLI entry point
5. **Executed refactor** with behavioral preservation as primary constraint

## Root Cause

Initial hackathon-style development prioritized speed over architecture, accumulating all logic in a single entry point file. As functionality grew, the module became a "god object" handling too many responsibilities.

## Working Solution

### Module Structure

Created focused modules with clear responsibilities:

```python
# src/safe_journalist/__init__.py (after refactor)
from safe_journalist.cli import main
from safe_journalist.client import encrypted_openai_call
from safe_journalist.session import MapleSession, create_session

__all__ = ["MapleSession", "create_session", "encrypted_openai_call", "main"]

if __name__ == "__main__":
    main()
```

### Crypto Layer (`crypto.py`)

Isolated base64 and encryption primitives:

```python
import base64
from nacl.secret import SecretBox

def _b64encode(data: bytes) -> str:
    """Base64 encode bytes to URL-safe string without padding."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def _b64decode(data: str) -> bytes:
    """Base64 decode URL-safe string, adding padding if needed."""
    padding = (4 - len(data) % 4) % 4
    return base64.urlsafe_b64decode(data + "=" * padding)

def encrypt_chacha20poly1305(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt with ChaCha20-Poly1305, prepend 12-byte nonce."""
    # Implementation details...
    pass

def decrypt_chacha20poly1305(key: bytes, ciphertext: bytes) -> bytes:
    """Decrypt ChaCha20-Poly1305 ciphertext with prepended nonce."""
    # Implementation details...
    pass
```

### Attestation Layer (`attestation.py`)

Isolated COSE document parsing:

```python
import cbor2
from safe_journalist.crypto import _b64decode

def _extract_public_key_from_attestation(attestation_document_b64: str) -> bytes:
    """Extracts server public key from COSE_Sign1 attestation document.
    
    Hackathon-mode: this does NOT verify attestation. It only decodes CBOR and
    pulls out the `public_key` field from the payload.
    """
    raw = _b64decode(attestation_document_b64)
    
    # COSE_Sign1 is a CBOR array: [protected, unprotected, payload, signature]
    cose = cbor2.loads(raw)
    if not isinstance(cose, list) or len(cose) < 3:
        raise ValueError("Unexpected COSE structure in attestation document")
    
    payload = cose[2]
    doc = cbor2.loads(payload)
    
    if not isinstance(doc, dict) or "public_key" not in doc:
        raise ValueError("Attestation payload missing public_key")
    
    public_key = doc["public_key"]
    
    # Handle bytes or list[int] representations
    if isinstance(public_key, (bytes, bytearray)):
        return bytes(public_key)
    if isinstance(public_key, list):
        return bytes(int(x) for x in public_key)
    
    raise ValueError(f"Unsupported public_key type: {type(public_key)}")
```

### Session Layer (`session.py`)

Isolated session data model and creation workflow:

```python
from dataclasses import dataclass
from nacl.public import PrivateKey
from safe_journalist.attestation import _extract_public_key_from_attestation
from safe_journalist.crypto import decrypt_chacha20poly1305

@dataclass
class MapleSession:
    """Represents an encrypted session with the Maple AI API."""
    api_url: str
    api_key: str
    session_id: str
    session_key: bytes

def create_session(api_url: str, api_key: str, nonce: str) -> MapleSession:
    """Creates a new Maple session via attestation and key exchange."""
    # 1. Fetch attestation
    # 2. Extract server public key
    # 3. Generate client X25519 keypair
    # 4. POST key exchange
    # 5. Decrypt session key with shared secret
    # Returns MapleSession with decrypted session_key
    pass
```

### Client Layer (`client.py`)

Isolated HTTP transport:

```python
import json
from safe_journalist.session import MapleSession
from safe_journalist.crypto import encrypt_chacha20poly1305, decrypt_chacha20poly1305

def encrypted_openai_call(session: MapleSession, path: str, payload: dict) -> dict:
    """Makes an encrypted OpenAI-compatible API call through Maple."""
    # 1. JSON-encode payload
    # 2. Encrypt with session key
    # 3. POST with headers:
    #    - Authorization: Bearer {api_key}
    #    - x-session-id: {session_id}
    #    - Accept-Encoding: identity
    # 4. Decrypt response
    pass
```

### CLI Layer (`cli.py`)

Isolated CLI entry point:

```python
import os
import sys
from safe_journalist.session import create_session
from safe_journalist.client import encrypted_openai_call

def main():
    """CLI entry point for encrypted OpenAI calls via Maple."""
    api_url = os.environ.get("MAPLE_API_URL")
    api_key = os.environ.get("MAPLE_API_KEY")
    nonce = os.environ.get("MAPLE_NONCE", "test-nonce")
    
    if not api_url or not api_key:
        print("Error: MAPLE_API_URL and MAPLE_API_KEY required", file=sys.stderr)
        sys.exit(1)
    
    session = create_session(api_url, api_key, nonce)
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": "Hello, world!"}]
    }
    
    response = encrypted_openai_call(session, "/v1/messages", payload)
    print(response)
```

## Code Review Finding

**Low Severity**: COSE array validation accepts length 3 instead of requiring 4 elements

```python
# attestation.py:17-18
if not isinstance(cose, list) or len(cose) < 3:
    raise ValueError("Unexpected COSE structure in attestation document")
```

COSE_Sign1 is specified as `[protected, unprotected, payload, signature]` (4 elements). Current code accepts arrays with 3+ elements, which could mask malformed documents missing the signature element.

**Fix**: Change validation to `len(cose) != 4` for strict compliance:

```python
if not isinstance(cose, list) or len(cose) != 4:
    raise ValueError("COSE_Sign1 must have exactly 4 elements")
```

## Prevention Strategies

### 1. Module Design Principles
- **Single Responsibility**: Each module handles one concern
- **Clear Boundaries**: Data flow follows crypto → attestation → session → client → CLI
- **Minimal Public API**: `__init__.py` exposes only public functions/classes

### 2. Early Refactoring Triggers
Watch for these signals in any module:
- ⚠️ File exceeds 200 lines
- ⚠️ More than 3 distinct concerns (crypto, HTTP, parsing, etc.)
- ⚠️ Difficult to write focused unit tests
- ⚠️ Import graph shows circular dependencies

### 3. Refactoring Checklist
- [ ] Identify module boundaries by grouping related functions
- [ ] Document behavioral contracts before moving code
- [ ] Create new modules with clear docstrings
- [ ] Update imports systematically
- [ ] Verify existing tests still pass
- [ ] Update `__init__.py` to expose public API

### 4. Testing Strategy
- Write unit tests for each new module in isolation
- Keep integration tests at the CLI level
- Mock HTTP calls in session/client tests
- Test error paths (invalid COSE, decryption failures, etc.)

## Related Documentation

- [Separation of Concerns Principle](https://en.wikipedia.org/wiki/Separation_of_concerns)
- [Python Module Design Best Practices](https://docs.python-guide.org/writing/structure/)
- [COSE_Sign1 Specification](https://datatracker.ietf.org/doc/html/rfc8152#section-4.2)

## Verification

After refactor, verified:
- ✅ All imports resolve correctly
- ✅ CLI still functions identically (env parsing, API call, response output)
- ✅ Behavioral flow unchanged (attestation → key exchange → encrypted call)
- ✅ Public API surface preserved in `__init__.py`
- ✅ Module dependency graph is acyclic and logical

## Files Modified

**Created:**
- `src/safe_journalist/crypto.py`
- `src/safe_journalist/attestation.py`
- `src/safe_journalist/session.py`
- `src/safe_journalist/client.py`
- `src/safe_journalist/cli.py`

**Updated:**
- `src/safe_journalist/__init__.py` (reduced to 10 lines, re-exports only)

## Tags

`#refactoring` `#separation-of-concerns` `#python-architecture` `#code-organization` `#technical-debt`
