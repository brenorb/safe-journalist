import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(data_b64: str) -> bytes:
    return base64.b64decode(data_b64)


def encrypt_chacha20_poly1305(*, key: bytes, plaintext: bytes) -> bytes:
    aead = ChaCha20Poly1305(key)
    nonce12 = os.urandom(12)
    return nonce12 + aead.encrypt(nonce12, plaintext, None)


def decrypt_chacha20_poly1305(*, key: bytes, encrypted: bytes) -> bytes:
    aead = ChaCha20Poly1305(key)
    nonce12 = encrypted[:12]
    ciphertext = encrypted[12:]
    return aead.decrypt(nonce12, ciphertext, None)
