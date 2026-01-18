import uuid
from dataclasses import dataclass

import httpx
from nacl import bindings
from nacl.public import PrivateKey

from safe_journalist.attestation import _extract_public_key_from_attestation
from safe_journalist.crypto import _b64decode, _b64encode, decrypt_chacha20_poly1305


@dataclass(frozen=True)
class MapleSession:
    api_url: str
    session_id: str
    session_key: bytes  # 32 bytes


def create_session(*, api_url: str, api_key: str | None, client: httpx.Client) -> MapleSession:
    normalized_api_url = api_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    nonce = str(uuid.uuid4())

    # 1) Fetch attestation document
    att = client.get(f"{normalized_api_url}/attestation/{nonce}", headers=headers)
    att.raise_for_status()
    att_doc_b64 = att.json()["attestation_document"]

    server_public_key = _extract_public_key_from_attestation(att_doc_b64)

    # 2) Generate client X25519 keypair (NaCl box keys)
    client_sk = PrivateKey.generate()
    client_pk = bytes(client_sk.public_key)

    # 3) Key exchange
    kx = client.post(
        f"{normalized_api_url}/key_exchange",
        headers=headers,
        json={"client_public_key": _b64encode(client_pk), "nonce": nonce},
    )
    kx.raise_for_status()
    kx_json = kx.json()

    encrypted_session_key = _b64decode(kx_json["encrypted_session_key"])
    session_id = kx_json["session_id"]

    # 4) Derive shared secret and decrypt session key
    shared_secret = bindings.crypto_scalarmult(bytes(client_sk), server_public_key)
    session_key = decrypt_chacha20_poly1305(key=shared_secret, encrypted=encrypted_session_key)

    return MapleSession(api_url=normalized_api_url, session_id=session_id, session_key=session_key)
