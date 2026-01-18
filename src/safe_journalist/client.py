import json

import httpx

from safe_journalist.crypto import _b64decode, _b64encode, decrypt_chacha20_poly1305, encrypt_chacha20_poly1305
from safe_journalist.session import MapleSession


def encrypted_openai_call(
    *,
    session: MapleSession,
    api_key: str,
    path: str,
    payload: dict,
    client: httpx.Client,
) -> dict:
    plaintext = json.dumps(payload).encode("utf-8")
    enc = encrypt_chacha20_poly1305(key=session.session_key, plaintext=plaintext)

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
    dec = decrypt_chacha20_poly1305(key=session.session_key, encrypted=encrypted_resp)
    return json.loads(dec.decode("utf-8"))
