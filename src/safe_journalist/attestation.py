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
