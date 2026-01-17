import base64
import json
import os
import uuid
from dataclasses import dataclass

import cbor2
import httpx
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from dotenv import load_dotenv
from nacl import bindings
from nacl.public import PrivateKey


@dataclass(frozen=True)
class MapleSession:
    api_url: str
    session_id: str
    session_key: bytes  # 32 bytes


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(data_b64: str) -> bytes:
    return base64.b64decode(data_b64)


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
    if not isinstance(payload, (bytes, bytearray)):
        raise ValueError("Unexpected payload type in COSE")

    doc = cbor2.loads(payload)
    if not isinstance(doc, dict) or "public_key" not in doc:
        raise ValueError("Attestation payload missing public_key")

    public_key = doc["public_key"]

    # The SDK treats this as a byte array.
    if isinstance(public_key, (bytes, bytearray)):
        return bytes(public_key)

    if isinstance(public_key, list):
        return bytes(int(x) for x in public_key)

    raise ValueError(f"Unsupported public_key type: {type(public_key)}")


def create_session(*, api_url: str, api_key: str, client: httpx.Client) -> MapleSession:
    nonce = str(uuid.uuid4())

    # 1) Fetch attestation document
    att = client.get(f"{api_url}/attestation/{nonce}")
    att.raise_for_status()
    att_doc_b64 = att.json()["attestation_document"]

    server_public_key = _extract_public_key_from_attestation(att_doc_b64)

    # 2) Generate client X25519 keypair (NaCl box keys)
    client_sk = PrivateKey.generate()
    client_pk = bytes(client_sk.public_key)

    # 3) Key exchange
    kx = client.post(
        f"{api_url}/key_exchange",
        json={"client_public_key": _b64encode(client_pk), "nonce": nonce},
    )
    kx.raise_for_status()
    kx_json = kx.json()

    encrypted_session_key = _b64decode(kx_json["encrypted_session_key"])
    session_id = kx_json["session_id"]

    # 4) Derive shared secret and decrypt session key
    shared_secret = bindings.crypto_scalarmult(bytes(client_sk), server_public_key)

    aead = ChaCha20Poly1305(shared_secret)
    nonce12 = encrypted_session_key[:12]
    ciphertext = encrypted_session_key[12:]
    session_key = aead.decrypt(nonce12, ciphertext, None)

    return MapleSession(api_url=api_url, session_id=session_id, session_key=session_key)


def encrypted_openai_call(
    *,
    session: MapleSession,
    api_key: str,
    path: str,
    payload: dict,
    client: httpx.Client,
) -> dict:
    plaintext = json.dumps(payload).encode("utf-8")

    aead = ChaCha20Poly1305(session.session_key)
    n = os.urandom(12)
    enc = n + aead.encrypt(n, plaintext, None)

    resp = client.post(
        f"{session.api_url}{path}",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-session-id": session.session_id,
            "Accept-Encoding": "identity",
        },
        json={"encrypted": _b64encode(enc)},
    )
    resp.raise_for_status()

    encrypted_resp = _b64decode(resp.json()["encrypted"])
    nonce12 = encrypted_resp[:12]
    ciphertext = encrypted_resp[12:]

    dec = aead.decrypt(nonce12, ciphertext, None)
    return json.loads(dec.decode("utf-8"))


def main() -> None:
    load_dotenv()

    api_url = os.getenv("MAPLE_API_URL", "https://enclave.trymaple.ai").rstrip("/")
    api_key = os.getenv("MAPLE_API_KEY")
    model = os.getenv("MAPLE_MODEL", "llama-3.3-70b")

    if not api_key:
        raise SystemExit("MAPLE_API_KEY is not set. Copy .env.example to .env and fill it.")

    with httpx.Client(timeout=60.0) as client:
        session = create_session(api_url=api_url, api_key=api_key, client=client)
        result = encrypted_openai_call(
            session=session,
            api_key=api_key,
            path="/v1/chat/completions",
            payload={
                "model": model,
                "messages": [
                    {"role": "user", "content": "who are you?"}
                ],
                "stream": False,
            },
            client=client,
        )

    text = (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    print(text)


if __name__ == "__main__":
    main()
