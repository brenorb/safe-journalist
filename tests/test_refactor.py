import base64
import io
import json
import os
import uuid
from unittest import TestCase
from unittest.mock import MagicMock, patch

import cbor2
import httpx
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from nacl import bindings
from nacl.public import PrivateKey

from safe_journalist.attestation import _extract_public_key_from_attestation
from safe_journalist.client import encrypted_openai_call
from safe_journalist.session import MapleSession, create_session


def _make_attestation(public_key: object) -> str:
    payload = cbor2.dumps({"public_key": public_key})
    cose = [b"", {}, payload, b"sig"]
    raw = cbor2.dumps(cose)
    return base64.b64encode(raw).decode("ascii")


class TestAttestation(TestCase):
    def test_extract_public_key_bytes(self) -> None:
        public_key = b"\x01\x02\x03"
        attestation_b64 = _make_attestation(public_key)

        result = _extract_public_key_from_attestation(attestation_b64)

        self.assertEqual(result, public_key)

    def test_extract_public_key_list(self) -> None:
        public_key_list = [1, 2, 3]
        attestation_b64 = _make_attestation(public_key_list)

        result = _extract_public_key_from_attestation(attestation_b64)

        self.assertEqual(result, bytes(public_key_list))

    def test_extract_public_key_invalid_type(self) -> None:
        attestation_b64 = _make_attestation("not-bytes")

        with self.assertRaises(ValueError):
            _extract_public_key_from_attestation(attestation_b64)


class TestSession(TestCase):
    def test_create_session_decrypts_session_key(self) -> None:
        api_url = "https://example.com"
        api_key = "test-key"
        nonce = uuid.UUID("12345678-1234-5678-1234-567812345678")

        client_sk_bytes = bytes(range(1, 33))
        client_sk = PrivateKey(client_sk_bytes)
        client_pk = bytes(client_sk.public_key)

        server_sk_bytes = bytes(range(33, 65))
        server_sk = PrivateKey(server_sk_bytes)
        server_pk = bytes(server_sk.public_key)

        attestation_b64 = _make_attestation(server_pk)

        shared_secret = bindings.crypto_scalarmult(bytes(client_sk), server_pk)
        session_key = b"\x11" * 32
        aead = ChaCha20Poly1305(shared_secret)
        nonce12 = b"\x00" * 12
        encrypted_session_key = nonce12 + aead.encrypt(nonce12, session_key, None)
        encrypted_session_key_b64 = base64.b64encode(encrypted_session_key).decode("ascii")

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.startswith("/attestation/"):
                return httpx.Response(
                    200,
                    json={"attestation_document": attestation_b64},
                )
            if request.url.path == "/key_exchange":
                body = json.loads(request.content.decode("utf-8"))
                self.assertEqual(body["client_public_key"], base64.b64encode(client_pk).decode("ascii"))
                self.assertEqual(body["nonce"], str(nonce))
                return httpx.Response(
                    200,
                    json={
                        "encrypted_session_key": encrypted_session_key_b64,
                        "session_id": "session-123",
                    },
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as client:
            with patch("safe_journalist.session.PrivateKey.generate", return_value=client_sk):
                with patch("safe_journalist.session.uuid.uuid4", return_value=nonce):
                    session = create_session(api_url=api_url, api_key=api_key, client=client)

        self.assertEqual(session.session_id, "session-123")
        self.assertEqual(session.session_key, session_key)
        self.assertEqual(session.api_url, api_url)


class TestClient(TestCase):
    def test_encrypted_openai_call_roundtrip(self) -> None:
        api_url = "https://example.com"
        session_key = b"\x22" * 32
        session = MapleSession(api_url=api_url, session_id="sess-1", session_key=session_key)
        payload = {"model": "m", "messages": [{"role": "user", "content": "ping"}]}
        api_key = "api-key"

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers.get("x-session-id"), "sess-1")
            self.assertEqual(request.headers.get("Authorization"), f"Bearer {api_key}")
            body = json.loads(request.content.decode("utf-8"))
            encrypted = base64.b64decode(body["encrypted"])
            nonce12 = encrypted[:12]
            ciphertext = encrypted[12:]
            aead = ChaCha20Poly1305(session_key)
            plaintext = aead.decrypt(nonce12, ciphertext, None)
            self.assertEqual(json.loads(plaintext.decode("utf-8")), payload)

            response_payload = {"choices": [{"message": {"content": "pong"}}]}
            resp_plaintext = json.dumps(response_payload).encode("utf-8")
            resp_nonce = b"\x01" * 12
            resp_encrypted = resp_nonce + aead.encrypt(resp_nonce, resp_plaintext, None)

            return httpx.Response(
                200,
                json={"encrypted": base64.b64encode(resp_encrypted).decode("ascii")},
            )

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as client:
            with patch("safe_journalist.crypto.os.urandom", return_value=b"\x09" * 12):
                result = encrypted_openai_call(
                    session=session,
                    api_key=api_key,
                    path="/v1/chat/completions",
                    payload=payload,
                    client=client,
                )

        self.assertEqual(result, {"choices": [{"message": {"content": "pong"}}]})


class TestCli(TestCase):
    def test_main_prints_message_content(self) -> None:
        from safe_journalist import cli

        session = MapleSession(
            api_url="https://example.com",
            session_id="sess-1",
            session_key=b"\x33" * 32,
        )

        fake_result = {"choices": [{"message": {"content": "hello"}}]}
        stdout = io.StringIO()

        with patch.dict(
            os.environ,
            {
                "MAPLE_API_URL": "https://example.com",
                "MAPLE_API_KEY": "api-key",
                "MAPLE_MODEL": "model-x",
            },
            clear=True,
        ):
            with patch("safe_journalist.cli.httpx.Client") as client_cls:
                client_instance = MagicMock()
                client_cls.return_value.__enter__.return_value = client_instance
                client_cls.return_value.__exit__.return_value = None
                with patch("safe_journalist.cli.create_session", return_value=session):
                    with patch("safe_journalist.cli.encrypted_openai_call", return_value=fake_result):
                        with patch("sys.stdout", stdout):
                            cli.main()

        self.assertEqual(stdout.getvalue().strip(), "hello")
